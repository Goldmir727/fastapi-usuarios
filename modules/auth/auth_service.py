from datetime import datetime, timezone, timedelta
from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from core.security import verify_password, create_access_token, create_refresh_token, create_reset_token
from core.config import settings
from core.email import notify_account_locked, notify_password_reset
from core.logger import logger


class AuthService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def login(self, username_in: str, password_in: str) -> dict:
        logger.info(f"Intento de login para: {username_in}")

        query = text("""
            SELECT id, username, email, hashed_password, is_active, validated_email,
                   failed_attempts, locked_until, role_id
            FROM users WHERE username = :username;
        """)
        result = await self.db.execute(query, {"username": username_in})
        user = result.mappings().first()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Usuario o contraseña incorrectos.",
                headers={"WWW-Authenticate": "Bearer"}
            )

        if not user["is_active"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Usuario inactivo.")

        if user["locked_until"] and user["locked_until"] > datetime.now(timezone.utc):
            remaining = int((user["locked_until"] - datetime.now(timezone.utc)).total_seconds() // 60)
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail=f"Cuenta bloqueada por actividad sospechosa. Intenta de nuevo en {remaining} minuto(s)."
            )

        if user["locked_until"] and user["locked_until"] <= datetime.now(timezone.utc):
            await self._reset_failed_attempts(user["id"])

        if not verify_password(password_in, user["hashed_password"]):
            await self._register_failed_attempt(user["id"], user["username"], user["email"])
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Usuario o contraseña incorrectos.",
                headers={"WWW-Authenticate": "Bearer"}
            )

        await self._reset_failed_attempts(user["id"])

        access_token = create_access_token(data={
            "sub": user["username"],
            "user_id": user["id"],
            "role_id": user["role_id"]
        })

        refresh_raw, refresh_hash = create_refresh_token()
        await self._store_refresh_token(user["id"], refresh_hash)

        return {
            "access_token": access_token,
            "refresh_token": refresh_raw,
            "token_type": "bearer"
        }

    async def refresh_access_token(self, refresh_token_raw: str) -> dict:
        from hashlib import sha256
        token_hash = sha256(refresh_token_raw.encode()).hexdigest()

        query = text("""
            SELECT rt.id, rt.user_id, rt.expires_at, rt.revoked,
                   u.username, u.role_id, u.is_active, u.locked_until
            FROM refresh_tokens rt
            INNER JOIN users u ON rt.user_id = u.id
            WHERE rt.token_hash = :token_hash;
        """)
        result = await self.db.execute(query, {"token_hash": token_hash})
        row = result.mappings().first()

        if not row or row["revoked"] or row["expires_at"] < datetime.now(timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token inválido o expirado."
            )

        if not row["is_active"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Usuario inactivo.")

        if row["locked_until"] and row["locked_until"] > datetime.now(timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail="Cuenta bloqueada por actividad sospechosa."
            )

        await self.db.execute(
            text("UPDATE refresh_tokens SET revoked = TRUE WHERE id = :id;"),
            {"id": row["id"]}
        )
        await self.db.commit()

        access_token = create_access_token(data={
            "sub": row["username"],
            "user_id": row["user_id"],
            "role_id": row["role_id"]
        })

        new_refresh_raw, new_refresh_hash = create_refresh_token()
        await self._store_refresh_token(row["user_id"], new_refresh_hash)

        return {
            "access_token": access_token,
            "refresh_token": new_refresh_raw,
            "token_type": "bearer"
        }

    async def forgot_password(self, email: str) -> dict:
        query = text("""
            SELECT id, username, email, validated_email, is_active
            FROM users WHERE email = :email;
        """)
        result = await self.db.execute(query, {"email": email})
        user = result.mappings().first()

        if not user or not user["is_active"]:
            return {"message": "Si el correo está registrado, recibirás instrucciones para restablecer tu contraseña."}

        reset_raw, reset_hash = create_reset_token()
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.RESET_TOKEN_EXPIRE_MINUTES)

        await self.db.execute(
            text("""
                INSERT INTO password_reset_tokens (user_id, token_hash, expires_at, used)
                VALUES (:user_id, :token_hash, :expires_at, FALSE);
            """),
            {"user_id": user["id"], "token_hash": reset_hash, "expires_at": expires_at}
        )
        await self.db.commit()

        await notify_password_reset(user["email"], user["username"], reset_raw)

        return {"message": "Si el correo está registrado, recibirás instrucciones para restablecer tu contraseña."}

    async def reset_password(self, token: str, new_password: str) -> dict:
        from hashlib import sha256
        from core.security import hash_password

        token_hash = sha256(token.encode()).hexdigest()

        query = text("""
            SELECT prt.id, prt.user_id, prt.expires_at, prt.used,
                   u.is_active, u.locked_until
            FROM password_reset_tokens prt
            INNER JOIN users u ON prt.user_id = u.id
            WHERE prt.token_hash = :token_hash;
        """)
        result = await self.db.execute(query, {"token_hash": token_hash})
        row = result.mappings().first()

        if not row or row["used"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token inválido o ya utilizado."
            )

        if row["expires_at"] < datetime.now(timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El token ha expirado. Solicita un nuevo restablecimiento."
            )

        if not row["is_active"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Usuario inactivo.")

        if row["locked_until"] and row["locked_until"] > datetime.now(timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail="Cuenta bloqueada. No se puede restablecer la contraseña en este estado."
            )

        hashed_pwd = hash_password(new_password)

        await self.db.execute(
            text("UPDATE password_reset_tokens SET used = TRUE WHERE id = :id;"),
            {"id": row["id"]}
        )
        await self.db.execute(
            text("UPDATE users SET hashed_password = :hashed_password, failed_attempts = 0, locked_until = NULL WHERE id = :user_id;"),
            {"hashed_password": hashed_pwd, "user_id": row["user_id"]}
        )
        await self.db.commit()

        return {"message": "Contraseña restablecida exitosamente."}

    async def _register_failed_attempt(self, user_id: int, username: str, email: str) -> None:
        await self.db.execute(
            text("UPDATE users SET failed_attempts = failed_attempts + 1 WHERE id = :id;"),
            {"id": user_id}
        )
        await self.db.commit()

        result = await self.db.execute(
            text("SELECT failed_attempts FROM users WHERE id = :id;"),
            {"id": user_id}
        )
        current_attempts = result.mappings().first()["failed_attempts"]

        if current_attempts >= settings.MAX_FAILED_ATTEMPTS:
            lock_until = datetime.now(timezone.utc) + timedelta(minutes=settings.LOCK_DURATION_MINUTES)
            await self.db.execute(
                text("UPDATE users SET locked_until = :locked_until WHERE id = :id;"),
                {"locked_until": lock_until, "id": user_id}
            )
            await self.db.commit()
            logger.warning(f"Cuenta bloqueada: {username} (ID: {user_id}) hasta {lock_until}")

            await notify_account_locked(email, username, settings.LOCK_DURATION_MINUTES)

    async def _reset_failed_attempts(self, user_id: int) -> None:
        await self.db.execute(
            text("UPDATE users SET failed_attempts = 0, locked_until = NULL WHERE id = :id;"),
            {"id": user_id}
        )
        await self.db.commit()

    async def _store_refresh_token(self, user_id: int, token_hash: str) -> None:
        expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        await self.db.execute(
            text("""
                INSERT INTO refresh_tokens (user_id, token_hash, expires_at)
                VALUES (:user_id, :token_hash, :expires_at);
            """),
            {"user_id": user_id, "token_hash": token_hash, "expires_at": expires_at}
        )
        await self.db.commit()
