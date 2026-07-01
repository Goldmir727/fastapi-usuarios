from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from modules.roles.role_schema import RoleCreate
from core.logger import logger


class RoleService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_all_roles(self) -> list[dict]:
        logger.info("SQL Nativo: Consultando todos los roles.")
        query = text("SELECT id, name, description FROM roles ORDER BY id ASC;")
        result = await self.db.execute(query)
        return [dict(row) for row in result.mappings().all()]

    async def get_role_by_name(self, role_name: str) -> list[dict]:
        logger.info(f"SQL Nativo: Consultando rol por nombre: {role_name}")
        query = text("SELECT id, name, description FROM roles WHERE name LIKE :name")
        result = await self.db.execute(query, {"name": f"%{role_name}%"})
        return [dict(row) for row in result.mappings().all()]
    
    async def get_role_by_id(self, role_id: int) -> dict:
        logger.info(f"SQL Nativo: Consultando rol por id: {role_id}")
        query = text("SELECT id, name, description FROM roles WHERE id = :id")
        result = await self.db.execute(query, {"id": role_id})
        row = result.mappings().first()
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rol no encontrado.")
        return dict(row)
    async def create_role(self, role_data: RoleCreate) -> dict:
        logger.info(f"SQL Nativo: Insertando rol {role_data.name}")

        check = await self.db.execute(text("SELECT id FROM roles WHERE name = :name;"), {"name": role_data.name})
        if check.first():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El rol ya existe.")

        query = text("INSERT INTO roles (name, description) VALUES (:name, :description) RETURNING id, name, description;")
        try:
            result = await self.db.execute(query, {"name": role_data.name, "description": role_data.description})
            await self.db.commit()
            row = result.mappings().first()
            if not row:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al obtener el rol insertado.")
            return dict(row.items())
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error al insertar rol: {str(e)}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interno del servidor.")

    async def delete_role_by_id(self, role_id: int) -> dict:
        logger.info(f"SQL Nativo: Eliminando rol por id: {role_id}")
        check = await self.db.execute(text("SELECT id FROM roles WHERE id = :id"), {"id": role_id})
        if not check.first():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rol no encontrado.")
        query = text("DELETE FROM roles WHERE id = :id RETURNING id, name, description;")
        result = await self.db.execute(query, {"id": role_id})
        await self.db.commit()
        row = result.mappings().first()
        if not row:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al obtener el rol eliminado.")
        return dict(row.items())
