from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from backend.api.payment_routes import router as payment_router
from backend.database import create_database


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    create_database()
    yield


app = FastAPI(
    title="AI Quality Engineering Platform",
    description="AI-powered Quality Engineering and Test Automation Platform",
    version="1.0.0",
    lifespan=lifespan,
)


app.include_router(payment_router)


@app.get("/")
def root():
    return {
        "message": "Welcome to AI Quality Engineering Platform",
        "status": "running"
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "application": "AI Quality Engineering Platform",
        "version": "1.0.0"
    }