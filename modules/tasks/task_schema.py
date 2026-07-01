from pydantic import BaseModel, Field, ConfigDict
from datetime import date
from typing import Optional


class TaskBase(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=200)
    descripcion: Optional[str] = None
    fecha_vencimiento: date
    responsable_id: int = Field(..., gt=0)


class TaskCreate(TaskBase):
    pass


class TaskUpdate(BaseModel):
    nombre: Optional[str] = Field(None, min_length=1, max_length=200)
    descripcion: Optional[str] = None
    fecha_vencimiento: Optional[date] = None
    responsable_id: Optional[int] = Field(None, gt=0)


class TaskEstadoUpdate(BaseModel):
    estado: str = Field(..., pattern="^(En progreso|Finalizada|Pendiente|Eliminada)$")


class TaskResponse(TaskBase):
    id: int
    estado: str

    model_config = ConfigDict(from_attributes=True)
