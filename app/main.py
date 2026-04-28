from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.routers import auth, schedules, clients, services, finance

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: here we could verify DB connection or load caches
    yield
    # Shutdown logic

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
    description="API para o sistema de gestão de barbearia Richardson Barber.",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(schedules.router, prefix="/api/v1")
app.include_router(clients.router, prefix="/api/v1")
app.include_router(services.router, prefix="/api/v1")
app.include_router(finance.router, prefix="/api/v1")


@app.get("/health", tags=["system"])
async def health_check():
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }
