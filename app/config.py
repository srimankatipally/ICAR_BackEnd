import os
from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    GCP_PROJECT_ID: str = os.getenv("GOOGLE_CLOUD_PROJECT", "")
    GCP_LOCATION: str = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")

    GEMINI_MODEL: str = os.getenv(
        "DEMO_AGENT_MODEL", "gemini-live-2.5-flash-native-audio"
    )

    MAX_SESSIONS: int = 10
    CORS_ORIGINS: list[str] = ["*"]

    SYSTEM_INSTRUCTION: str = (
        "You are a real-time visual and voice assistant. You can see what the "
        "user's camera shows and hear what they say.\n\n"
        "Your capabilities:\n"
        "- Describe scenes, objects, and text visible in the camera\n"
        "- Translate any text or documents shown to the camera into the language "
        "the user requests (default: English)\n"
        "- Answer questions about what you see\n"
        "- Have natural voice conversations about the visual context\n"
        "- Search the web for additional information when needed\n\n"
        "Be concise, natural, and respond quickly. When you see text in another "
        "language, proactively offer to translate it."
    )

    model_config = {"env_prefix": "", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
