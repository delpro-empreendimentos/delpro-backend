from fastapi import APIRouter

chat_router = APIRouter(prefix="/chat", tags=["chat"])

@chat_router.get("/home")
async def is_alive():
    return {"detail": "Service is alive!"}