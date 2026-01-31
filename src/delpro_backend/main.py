"""Main file Delpro Backend."""

from fastapi import FastAPI

from delpro_backend.routes.v1.router import router

app = FastAPI()

app.include_router(router)


@app.get("/")
async def root():
    """Check if service is alive."""
    return {"detail": "Alive!"}
