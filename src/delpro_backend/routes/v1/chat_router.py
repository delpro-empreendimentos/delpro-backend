"""This module defines the roues for the Chat endpoints."""
from fastapi import APIRouter

chat_router = APIRouter(prefix="/chat", tags=["chat"])


@chat_router.get("/home")
async def is_alive():
    """Check if service is alive."""
    return {"detail": "Service is alive!"}
