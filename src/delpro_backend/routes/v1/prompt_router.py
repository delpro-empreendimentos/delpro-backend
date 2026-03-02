"""Router for agent prompt CRUD operations."""

from fastapi import APIRouter
from pydantic import BaseModel

from delpro_backend.assistant.prompt_loader import load_prompt_config
from delpro_backend.db.db_service import AsyncSessionFactory
from delpro_backend.models.v1.database_models import PromptRow
from delpro_backend.utils.handle_errors import handle_errors
from delpro_backend.utils.logger import get_logger

logger = get_logger(__name__)

prompt_router = APIRouter(prefix="/prompt", tags=["prompt"])

_PROMPT_ID = "main"


class PromptResponse(BaseModel):
    """Response model for the agent prompt."""

    content: str
    updated_at: str | None = None


class PromptUpdateRequest(BaseModel):
    """Request model for updating the agent prompt."""

    content: str


def _default_prompt() -> str:
    """Return the system_prompt from prompt.yml as the fallback default."""
    try:
        config = load_prompt_config()
        return config.get("system_prompt", "You are a helpful assistant.")
    except Exception:
        return "You are a helpful assistant."


@prompt_router.get("", response_model=PromptResponse)
@handle_errors
async def get_prompt():
    """Return the current agent system prompt.

    If no prompt exists in the database yet, seeds the row from prompt.yml.

    Returns:
        The current prompt content and last-updated timestamp.
    """
    async with AsyncSessionFactory() as session:
        row = await session.get(PromptRow, _PROMPT_ID)
        if row is None:
            content = _default_prompt()
            row = PromptRow(id=_PROMPT_ID, content=content)
            session.add(row)
            await session.commit()
            await session.refresh(row)
            logger.info("Seeded agent_prompt table from prompt.yml")

    return PromptResponse(
        content=row.content,
        updated_at=row.updated_at.isoformat() if row.updated_at else None,
    )


@prompt_router.put("", response_model=PromptResponse)
@handle_errors
async def update_prompt(data: PromptUpdateRequest):
    """Update the agent system prompt.

    Args:
        data: New prompt content.

    Returns:
        Updated prompt content and timestamp.
    """
    async with AsyncSessionFactory() as session:
        row = await session.get(PromptRow, _PROMPT_ID)
        if row is None:
            row = PromptRow(id=_PROMPT_ID, content=data.content)
            session.add(row)
        else:
            row.content = data.content
        await session.commit()
        await session.refresh(row)

    logger.info("Agent prompt updated (%d chars)", len(data.content))
    return PromptResponse(
        content=row.content,
        updated_at=row.updated_at.isoformat() if row.updated_at else None,
    )
