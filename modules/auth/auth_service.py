from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from core.security import verify_password, create_access_token
from core.logger import logger


class AuthService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def login(self, username_in: str, password_in: str) -> str:
        logger.info(f"SQL Nativo: Intento de login para: {username_in}")

        query = text("SELECT id, username, hashed_password, is_active, role_id FROM users WHERE username = :username;")
        result = await self.db.execute(query, {"username": username_in})
        user = result.mappings().first()

        if not user :
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Usuario no existe",
                headers={"WWW-Authenticate": "Bearer"}
            )
        if not verify_password(password_in, user["hashed_password"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Usuario no existe",
                headers={"WWW-Authenticate": "Bearer"}
            )

        if not user["is_active"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Usuario inactivo.")

        return create_access_token(data={"sub": user["username"], "user_id": user["id"], "role_id": user["role_id"]})
