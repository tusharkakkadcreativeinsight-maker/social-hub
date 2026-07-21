from typing import List, Literal, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..config import settings
from ..models.models import User
from ..utils.dependencies import get_current_user


router = APIRouter(prefix="/api/ai-chat", tags=["AI Chat"])


class AIChatMessage(BaseModel):
    role: Literal["user", "assistant", "system"] = "user"
    content: str = Field(..., min_length=1, max_length=4000)


class AIChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    history: List[AIChatMessage] = []


class AIChatResponse(BaseModel):
    reply: str
    model: Optional[str] = None
    using_fallback: bool = False


def build_local_reply(message: str, user: User) -> str:
    """Safe fallback when no OpenAI key is configured for local development."""
    name = user.full_name or user.username
    return (
        f"Hi {name}! AI chat is connected, but OPENAI_API_KEY is not configured yet. "
        f"You said: \"{message}\". Add OPENAI_API_KEY to SocialHub/.env to enable OpenAI replies."
    )


@router.post("", response_model=AIChatResponse)
async def chat_with_ai(
    request: AIChatRequest,
    current_user: User = Depends(get_current_user),
):
    """Send a prompt to OpenAI Chat Completions, with a local fallback for dev."""
    user_message = request.message.strip()
    if not user_message:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    if not settings.OPENAI_API_KEY:
        return AIChatResponse(reply=build_local_reply(user_message, current_user), using_fallback=True)

    messages = [
        {
            "role": "system",
            "content": "You are SocialHub AI, a helpful assistant inside a social media messaging app. Keep replies friendly, concise, and safe.",
        }
    ]
    for item in request.history[-12:]:
        messages.append({"role": item.role, "content": item.content})
    messages.append({"role": "user", "content": user_message})

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.OPENAI_MODEL,
                    "messages": messages,
                    "temperature": 0.7,
                    "max_tokens": 500,
                },
            )
        if response.status_code >= 400:
            detail = response.json().get("error", {}).get("message", "OpenAI request failed")
            raise HTTPException(status_code=502, detail=detail)
        data = response.json()
        reply = data["choices"][0]["message"]["content"].strip()
        return AIChatResponse(reply=reply, model=settings.OPENAI_MODEL)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"AI chat failed: {exc}")