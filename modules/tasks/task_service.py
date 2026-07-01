from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from modules.tasks.task_schema import TaskCreate, TaskUpdate, TaskEstadoUpdate
from core.logger import logger


class TaskService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_all_tasks(self) -> list[dict]:
        logger.info("SQL Nativo: Consultando todas las tareas.")
        query = text("""
            SELECT t.id, t.nombre, t.descripcion, t.fecha_vencimiento,
                   t.responsable_id, u.username as responsable_nombre, t.estado
            FROM tasks t
            JOIN users u ON u.id = t.responsable_id
            ORDER BY t.id ASC;
        """)
        result = await self.db.execute(query)
        return [dict(row) for row in result.mappings().all()]

    async def get_tasks_by_responsable(self, responsable_id: int) -> list[dict]:
        logger.info(f"SQL Nativo: Consultando tareas del responsable {responsable_id}.")

        user_check = await self.db.execute(
            text("SELECT id, username FROM users WHERE id = :id;"),
            {"id": responsable_id}
        )
        user = user_check.mappings().first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="El responsable no existe.")

        query = text("""
            SELECT t.id, t.nombre, t.descripcion, t.fecha_vencimiento,
                   t.responsable_id, u.username as responsable_nombre, t.estado
            FROM tasks t
            JOIN users u ON u.id = t.responsable_id
            WHERE t.responsable_id = :responsable_id
            ORDER BY t.id ASC;
        """)
        result = await self.db.execute(query, {"responsable_id": responsable_id})
        return [dict(row) for row in result.mappings().all()]

    async def create_task(self, task_data: TaskCreate) -> dict:
        logger.info(f"SQL Nativo: Creando tarea '{task_data.nombre}'.")

        user_check = await self.db.execute(
            text("SELECT id FROM users WHERE id = :id;"),
            {"id": task_data.responsable_id}
        )
        if not user_check.first():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El responsable_id no existe.")

        query = text("""
            INSERT INTO tasks (nombre, descripcion, fecha_vencimiento, responsable_id, estado)
            VALUES (:nombre, :descripcion, :fecha_vencimiento, :responsable_id, 'Pendiente')
            RETURNING id, nombre, descripcion, fecha_vencimiento, responsable_id, estado;
        """)
        try:
            result = await self.db.execute(query, {
                "nombre": task_data.nombre,
                "descripcion": task_data.descripcion,
                "fecha_vencimiento": task_data.fecha_vencimiento,
                "responsable_id": task_data.responsable_id,
            })
            await self.db.commit()
            return dict(result.mappings().first())
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error al crear tarea: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error al crear la tarea."
            )

    async def update_task(self, task_id: int, task_data: TaskUpdate) -> dict:
        logger.info(f"SQL Nativo: Actualizando tarea {task_id}.")

        existing = await self.db.execute(
            text("SELECT id FROM tasks WHERE id = :id;"),
            {"id": task_id}
        )
        if not existing.first():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="La tarea no existe.")

        if task_data.responsable_id is not None:
            user_check = await self.db.execute(
                text("SELECT id FROM users WHERE id = :id;"),
                {"id": task_data.responsable_id}
            )
            if not user_check.first():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="El responsable_id no existe."
                )

        set_parts = []
        params: dict = {"id": task_id}

        if task_data.nombre is not None:
            set_parts.append("nombre = :nombre")
            params["nombre"] = task_data.nombre
        if task_data.descripcion is not None:
            set_parts.append("descripcion = :descripcion")
            params["descripcion"] = task_data.descripcion
        if task_data.fecha_vencimiento is not None:
            set_parts.append("fecha_vencimiento = :fecha_vencimiento")
            params["fecha_vencimiento"] = task_data.fecha_vencimiento
        if task_data.responsable_id is not None:
            set_parts.append("responsable_id = :responsable_id")
            params["responsable_id"] = task_data.responsable_id

        if not set_parts:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No hay campos para actualizar."
            )

        set_clause = ", ".join(set_parts)
        query = text(f"""
            UPDATE tasks
            SET {set_clause}
            WHERE id = :id
            RETURNING id, nombre, descripcion, fecha_vencimiento, responsable_id, estado;
        """)
        try:
            result = await self.db.execute(query, params)
            await self.db.commit()
            return dict(result.mappings().first())
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error al actualizar tarea: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error al actualizar la tarea."
            )

    async def update_task_estado(self, task_id: int, estado_data: TaskEstadoUpdate) -> dict:
        logger.info(f"SQL Nativo: Actualizando estado de tarea {task_id} a '{estado_data.estado}'.")

        existing = await self.db.execute(
            text("SELECT id FROM tasks WHERE id = :id;"),
            {"id": task_id}
        )
        if not existing.first():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="La tarea no existe.")

        query = text("""
            UPDATE tasks
            SET estado = :estado
            WHERE id = :id
            RETURNING id, nombre, descripcion, fecha_vencimiento, responsable_id, estado;
        """)
        try:
            result = await self.db.execute(query, {"id": task_id, "estado": estado_data.estado})
            await self.db.commit()
            return dict(result.mappings().first())
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error al actualizar estado: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error al actualizar el estado."
            )
