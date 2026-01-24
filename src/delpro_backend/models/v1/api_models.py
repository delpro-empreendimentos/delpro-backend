"""File to store all v1 api models."""

from pydantic import BaseModel


class SendMessageRequest(BaseModel):
    """Request a LLM response."""

    input: str
