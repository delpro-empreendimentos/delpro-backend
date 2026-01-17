"""This module defines the roues for the Chat endpoints."""

from fastapi import APIRouter

chat_router = APIRouter(prefix="/chat", tags=["chat"])
