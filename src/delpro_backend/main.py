"""Main file Delpro Backend."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from delpro_backend.db.db_service import engine
from delpro_backend.db.models import Base
from delpro_backend.routes.v1.router import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: create ORM tables on startup."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(lifespan=lifespan)

app.include_router(router)


@app.get("/")
async def root():
    """Check if service is alive."""
    return {"detail": "Alive!"}
