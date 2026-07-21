from contextlib import asynccontextmanager
from fastapi import FastAPI
from modules.roles.role_router import router as role_router
from modules.users.user_router import router as user_router
from modules.auth.auth_router import router as auth_router
from modules.tasks.task_router import router as task_router
from core.logger import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("==========================================================")
    logger.info("  API Modular Inicializada en Raíz con Éxito (Lifespan)!")
    logger.info("  Documentación interactiva: http://127.0.0.1:8000/docs")
    logger.info("==========================================================")
    yield
    logger.info("Cerrando recursos de la API de forma segura.")


app = FastAPI(
    title="API FastAPI Modular sin SRC - SQL Puro",
    version="3.2.0",
    description="Estructura limpia basada en dominios directo en raíz - Ciberseguridad (RNF-01, RNF-02)",
    lifespan=lifespan
)

app.include_router(auth_router)
app.include_router(role_router)
app.include_router(user_router)
app.include_router(task_router)
