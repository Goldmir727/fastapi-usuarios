from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import get_db
from modules.tasks.task_schema import TaskCreate, TaskResponse, TaskUpdate, TaskEstadoUpdate
from modules.tasks.task_service import TaskService

router = APIRouter(prefix="/tasks", tags=["Tareas"])


@router.get("/", response_model=list[TaskResponse], status_code=status.HTTP_200_OK)
async def read_all_tasks(db: AsyncSession = Depends(get_db)):
    service = TaskService(db)
    return await service.get_all_tasks()


@router.get("/responsable/{responsable_id}", response_model=list[TaskResponse], status_code=status.HTTP_200_OK)
async def read_tasks_by_responsable(responsable_id: int, db: AsyncSession = Depends(get_db)):
    service = TaskService(db)
    return await service.get_tasks_by_responsable(responsable_id)


@router.post("/", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def add_task(task_in: TaskCreate, db: AsyncSession = Depends(get_db)):
    service = TaskService(db)
    return await service.create_task(task_in)


@router.put("/{task_id}", response_model=TaskResponse, status_code=status.HTTP_200_OK)
async def modify_task(task_id: int, task_in: TaskUpdate, db: AsyncSession = Depends(get_db)):
    service = TaskService(db)
    return await service.update_task(task_id, task_in)


@router.patch("/{task_id}/estado", response_model=TaskResponse, status_code=status.HTTP_200_OK)
async def change_task_estado(task_id: int, estado_in: TaskEstadoUpdate, db: AsyncSession = Depends(get_db)):
    service = TaskService(db)
    return await service.update_task_estado(task_id, estado_in)
