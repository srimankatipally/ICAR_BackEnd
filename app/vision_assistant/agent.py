"""Vision assistant agent for real-time camera + voice interactions."""

from google.adk.agents import Agent
from google.adk.tools import google_search

from app.config import settings

agent = Agent(
    name="vision_assistant",
    model=settings.GEMINI_MODEL,
    tools=[google_search],
    instruction=settings.SYSTEM_INSTRUCTION,
)
