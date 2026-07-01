from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import get_db
from core.security import get_current_user  # Nueva importación
from modules.users.user_schema import UserCreate, UserUpdate, UserResponse
from modules.users.user_service import UserService

router = APIRouter(prefix="/users", tags=["Usuarios"])

@router.get("/", response_model=list[UserResponse], status_code=status.HTTP_200_OK)
async def read_users(
    db: AsyncSession = Depends(get_db), 
    current_user: dict = Depends(get_current_user)
):
    """Acceso restringido: Solo un Administrador puede ver el pool de usuarios completo."""
    if current_user["role_name"] != "Administrador":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado. Rol insuficiente.")
    service = UserService(db)
    return await service.get_all_users()

@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def add_user(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    """Mantenido público intencionalmente para permitir el autoregistro inicial de aprendices."""
    service = UserService(db)
    return await service.create_user(user_in)

@router.put("/{user_id}", response_model=UserResponse, status_code=status.HTTP_200_OK)
async def update_existing_user(
    user_id: int, 
    user_data: UserUpdate, 
    db: AsyncSession = Depends(get_db), 
    current_user: dict = Depends(get_current_user)
):
    """
    Endpoint Protegido por Token y RBAC:
    - Admin: Modifica a cualquier usuario sin restricciones.
    - Aprendiz: Solo puede modificarse a sí mismo (restringido en capa de servicios).
    """
    service = UserService(db)
    return await service.update_user(user_id, user_data, current_user)