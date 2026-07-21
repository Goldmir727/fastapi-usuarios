from fastapi import APIRouter, Depends, status, Form
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import get_db
from modules.auth.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Autenticación"])


@router.post("/login", status_code=status.HTTP_200_OK)
async def sign_in(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    service = AuthService(db)
    return await service.login(form_data.username, form_data.password)


@router.post("/refresh", status_code=status.HTTP_200_OK)
async def refresh_token(refresh_token: str = Form(...), db: AsyncSession = Depends(get_db)):
    service = AuthService(db)
    return await service.refresh_access_token(refresh_token)


@router.post("/forgot-password", status_code=status.HTTP_200_OK)
async def forgot_password(email: str = Form(...), db: AsyncSession = Depends(get_db)):
    service = AuthService(db)
    return await service.forgot_password(email)


@router.post("/reset-password", status_code=status.HTTP_200_OK)
async def reset_password(token: str = Form(...), new_password: str = Form(...), db: AsyncSession = Depends(get_db)):
    service = AuthService(db)
    return await service.reset_password(token, new_password)
