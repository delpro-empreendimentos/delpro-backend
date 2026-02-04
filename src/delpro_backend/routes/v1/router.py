"""This module sets up the API v1 routes."""

from fastapi import APIRouter

from delpro_backend.routes.v1.chat_router import chat_router
from delpro_backend.routes.v1.documents_router import documents_router

router = APIRouter()
router.include_router(chat_router)
router.include_router(documents_router)
