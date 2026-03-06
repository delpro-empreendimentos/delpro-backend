"""Main file Delpro Backend."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from delpro_backend.db.db_service import engine
from delpro_backend.models.v1.database_models import Base
from delpro_backend.routes.v1.router import router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s:\t%(name)s - %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: create pgvector extension and ORM tables on startup."""
    async with engine.begin() as conn:
        # Enable pgvector extension
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))

        # Create all tables
        await conn.run_sync(Base.metadata.create_all)

        logging.info("Database tables ready (using exact vector search for 3072-dim embeddings)")

    yield


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/health")
async def health():
    """Check alive."""
    return {"status": "ok"}

@app.get("/")
async def root():
    """Check if service is alive."""
    return {"detail": "Alive!"}
