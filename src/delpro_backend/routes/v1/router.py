from fastapi import APIRouter
from delpro_backend.routes.v1.chat_router import chat_router


router = APIRouter()
router.include_router(chat_router)