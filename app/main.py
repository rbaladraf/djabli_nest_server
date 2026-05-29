from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import admin, admin_reports, admin_users, auth, files, health, mobile
from app.core.config import get_settings
from app.core.logging import setup_logging

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    yield


app = FastAPI(
    title="Djabli Nest API",
    description="VPS API Server for Djabli Nest Mobile & Djabli Nest Admin",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(mobile.router)
app.include_router(admin.router)
app.include_router(admin_reports.router)
app.include_router(admin_users.router)
app.include_router(files.router)
