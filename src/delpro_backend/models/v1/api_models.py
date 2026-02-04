"""File to store all v1 api models."""

from pydantic import BaseModel, Field


class SendMessageRequest(BaseModel):
    """Request to send a message to the assistant."""

    session_id: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Conversation identifier (e.g., WhatsApp phone number).",
        examples=["5511999990000"],
    )
    input: str = Field(
        ...,
        min_length=1,
        description="The user's message text.",
    )
    user_name: str = Field(
        ...,
        max_length=100,
        description="Broker's name from WhatsApp payload (contacts[0].profile.name).",
        examples=["Carlos Mendes"],
    )


class SendMessageResponse(BaseModel):
    """Response from the assistant."""

    session_id: str = Field(description="The session identifier echoed back.")
    response: str = Field(description="The assistant's text response.")
