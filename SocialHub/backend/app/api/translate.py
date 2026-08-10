"""Translation API - English ↔ Gujarati translation with voice support."""

from typing import Optional
import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..config import settings
from ..models.models import User
from ..utils.dependencies import get_current_user


router = APIRouter(prefix="/api/translate", tags=["Translation"])


class TranslateRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000)
    source_lang: str = Field(default="auto", pattern=r"^(auto|en|gu)$")
    target_lang: str = Field(..., pattern=r"^(en|gu)$")


class TranslateResponse(BaseModel):
    translated_text: str
    source_lang: str
    target_lang: str
    using_fallback: bool = False


# Gujarati phrase dictionary for offline fallback translation
GUJARATI_PHRASES = {
    # Greetings
    "hello": "નમસ્તે",
    "hi": "હાય",
    "good morning": "સુપ્રભાત",
    "good evening": "શુભ સાંજ",
    "good night": "શુભ રાત્રિ",
    "how are you": "તમે કેમ છો",
    "i am fine": "હું સારો છું",
    "thank you": "આભાર",
    "thanks": "આભાર",
    "welcome": "સ્વાગત છે",
    "bye": "આવજો",
    "goodbye": "આવજો",
    "see you": "ફરી મળીશું",
    # Common phrases
    "what is your name": "તમારું નામ શું છે",
    "my name is": "મારું નામ છે",
    "nice to meet you": "તમને મળીને આનંદ થયો",
    "please": "કૃપા કરીને",
    "sorry": "માફ કરશો",
    "excuse me": "માફ કરશો",
    "yes": "હા",
    "no": "ના",
    "ok": "ઠીક છે",
    "okay": "ઠીક છે",
    # Social media terms
    "post": "પોસ્ટ",
    "like": "લાઈક",
    "share": "શેર",
    "comment": "ટિપ્પણી",
    "follow": "અનુસરો",
    "follower": "અનુયાયી",
    "message": "સંદેશ",
    "notification": "સૂચના",
    "profile": "પ્રોફાઇલ",
    "photo": "ફોટો",
    "video": "વિડિઓ",
    "story": "વાર્તા",
    "reel": "રીલ",
    "trending": "ટ્રેન્ડિંગ",
    "explore": "અન્વેષણ",
    "search": "શોધ",
    "settings": "સેટિંગ્સ",
    "logout": "લોગઆઉટ",
    "login": "લોગિન",
    "register": "નોંધણી",
    "password": "પાસવર્ડ",
    "email": "ઈમેલ",
    "username": "વપરાશકર્તા નામ",
    # Time
    "today": "આજે",
    "tomorrow": "આવતીકાલે",
    "yesterday": "ગઈકાલે",
    "now": "હમણાં",
    "later": "પછીથી",
    "morning": "સવાર",
    "afternoon": "બપોર",
    "evening": "સાંજ",
    "night": "રાત્રિ",
    # Emotions
    "happy": "ખુશ",
    "sad": "ઉદાસ",
    "love": "પ્રેમ",
    "angry": "ગુસ્સો",
    "excited": "ઉત્સાહિત",
    "wonderful": "અદ્ભુત",
    "amazing": "અમેઝિંગ",
    "great": "મહાન",
    "good": "સારું",
    "bad": "ખરાબ",
    "beautiful": "સુંદર",
    # Numbers
    "one": "એક",
    "two": "બે",
    "three": "ત્રણ",
    "four": "ચાર",
    "five": "પાંચ",
}

# Reverse dictionary for Gujarati → English
ENGLISH_PHRASES = {v: k for k, v in GUJARATI_PHRASES.items()}


def fallback_translate(text: str, source_lang: str, target_lang: str) -> str:
    """Simple dictionary-based fallback translation for common phrases."""
    text_lower = text.lower().strip()
    
    if source_lang == "en" and target_lang == "gu":
        # English → Gujarati
        if text_lower in GUJARATI_PHRASES:
            return GUJARATI_PHRASES[text_lower]
        # Try partial match
        for eng, guj in GUJARATI_PHRASES.items():
            if eng in text_lower:
                return text.replace(eng, guj).replace(eng.capitalize(), guj)
        return f"[Gujarati: {text}]"
    
    elif source_lang == "gu" and target_lang == "en":
        # Gujarati → English
        if text_lower in ENGLISH_PHRASES:
            return ENGLISH_PHRASES[text_lower]
        return f"[English: {text}]"
    
    return text


@router.post("", response_model=TranslateResponse)
async def translate_text(
    request: TranslateRequest,
    current_user: User = Depends(get_current_user),
):
    """Translate text between English and Gujarati using AI or fallback dictionary."""
    text = request.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Text cannot be empty")
    
    source = request.source_lang
    target = request.target_lang
    
    # If source is auto, try to detect
    if source == "auto":
        # Simple detection: if text contains Gujarati Unicode characters
        has_gujarati = any('\u0A80' <= c <= '\u0AFF' for c in text)
        source = "gu" if has_gujarati else "en"
    
    # If OpenAI key is configured, use AI translation
    if settings.OPENAI_API_KEY:
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                lang_map = {"en": "English", "gu": "Gujarati"}
                source_name = lang_map.get(source, "English")
                target_name = lang_map.get(target, "English")
                
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": settings.OPENAI_MODEL,
                        "messages": [
                            {
                                "role": "system",
                                "content": (
                                    f"You are a translator. Translate the following text from {source_name} "
                                    f"to {target_name}. Return ONLY the translated text, nothing else. "
                                    f"Keep the tone and style of the original. If it's a social media post, "
                                    f"keep it natural and engaging."
                                ),
                            },
                            {"role": "user", "content": text},
                        ],
                        "temperature": 0.3,
                        "max_tokens": 1000,
                    },
                )
                if response.status_code >= 400:
                    detail = response.json().get("error", {}).get("message", "Translation request failed")
                    raise HTTPException(status_code=502, detail=detail)
                data = response.json()
                translated = data["choices"][0]["message"]["content"].strip()
                return TranslateResponse(
                    translated_text=translated,
                    source_lang=source,
                    target_lang=target,
                    using_fallback=False,
                )
        except HTTPException:
            raise
        except Exception as exc:
            # Fall back to dictionary on error
            translated = fallback_translate(text, source, target)
            return TranslateResponse(
                translated_text=translated,
                source_lang=source,
                target_lang=target,
                using_fallback=True,
            )
    
    # No OpenAI key - use fallback dictionary
    translated = fallback_translate(text, source, target)
    return TranslateResponse(
        translated_text=translated,
        source_lang=source,
        target_lang=target,
        using_fallback=True,
    )


class VoiceToTextRequest(BaseModel):
    audio_base64: Optional[str] = None
    language: str = Field(default="gu", pattern=r"^(en|gu|hi)$")


class VoiceToTextResponse(BaseModel):
    text: str
    language: str
    confidence: float = 1.0


@router.post("/voice-to-text", response_model=VoiceToTextResponse)
async def voice_to_text(
    request: VoiceToTextRequest,
    current_user: User = Depends(get_current_user),
):
    """Process voice input (speech-to-text).
    
    Note: Primary speech-to-text happens client-side using the Web Speech API.
    This endpoint is for server-side processing if needed in the future.
    """
    # For now, this is a placeholder. The actual speech-to-text
    # is handled by the browser's Web Speech API on the frontend.
    raise HTTPException(
        status_code=501,
        detail="Server-side speech-to-text is not yet implemented. "
               "Use the browser's Web Speech API for client-side recognition."
    )