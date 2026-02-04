"""This module defines the routes for the Chat endpoints."""

from fastapi import APIRouter

from delpro_backend.assistant.assistant_service import AssistantService
from delpro_backend.models.v1.api_models import SendMessageRequest, SendMessageResponse
from delpro_backend.utils.handle_errors import handle_errors

chat_router = APIRouter(prefix="/chat", tags=["chat"])

assistant_service = AssistantService()


@chat_router.post("", response_model=SendMessageResponse)
@handle_errors
async def send_message(request: SendMessageRequest) -> SendMessageResponse:
    """Send a message to the assistant and receive a response.

    Args:
        request: The message request containing session_id, input text, and user_name.

    Returns:
        The assistant's response with the session_id echoed back.
    """
    response_text = await assistant_service.chat(
        session_id=request.session_id,
        user_message=request.input,
        user_name=request.user_name,
    )

    return SendMessageResponse(
        session_id=request.session_id,
        response=response_text,
    )
