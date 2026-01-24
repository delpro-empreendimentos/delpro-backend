"""This module defines the roues for the Chat endpoints."""

from fastapi import APIRouter

from delpro_backend.models.v1.api_models import SendMessageRequest
from delpro_backend.utils.llm_builder import get_llm

chat_router = APIRouter(prefix="/chat", tags=["chat"])



llm = get_llm()


@chat_router.post("")
async def send_message(request: SendMessageRequest):
    """Send message endpoint."""
    message = await llm.ainvoke(request.input)
    return message
