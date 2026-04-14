"""Root live agent with direct function tools for fast response times."""

from google.adk.agents import Agent
from google.genai import types

from app.config import settings
from app.knowledge_agent.agent import get_crop_knowledge
from app.vision_assistant.agent import get_disease_knowledge

root_agent = Agent(
    name="icar_assistant",
    model=settings.GEMINI_MODEL,
    tools=[get_crop_knowledge, get_disease_knowledge],
    instruction=settings.SYSTEM_INSTRUCTION,
    generate_content_config=types.GenerateContentConfig(
        labels={"deployment": settings.DEPLOYMENT_TAG},
    ),
)
