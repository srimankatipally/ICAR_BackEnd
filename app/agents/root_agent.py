"""Root live agent that orchestrates knowledge and vision sub-agents via AgentTool."""

from google.adk.agents import Agent
from google.adk.tools.agent_tool import AgentTool

from app.config import settings
from app.knowledge_agent.agent import knowledge_agent
from app.vision_assistant.agent import vision_agent

root_agent = Agent(
    name="icar_assistant",
    model=settings.GEMINI_MODEL,
    tools=[
        AgentTool(agent=knowledge_agent, skip_summarization=True),
        AgentTool(agent=vision_agent, skip_summarization=True),
    ],
    instruction=settings.SYSTEM_INSTRUCTION,
)
