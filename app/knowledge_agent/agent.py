"""Knowledge agent that answers crop/agriculture questions using local .txt files."""

import json

from google.adk.agents import Agent
from google.genai import types

from app.config import settings
from app.knowledge.file_reader import KnowledgeBase

knowledge_base = KnowledgeBase(settings.CROP_DIR)

KNOWLEDGE_INSTRUCTION = """\
You are an Oilseeds Crop Knowledge Expert.

Goal: Answer the user's query about oilseed crops grounded ONLY in the
provided local text files.

Plan:
1) Decide the crop from the user's question.
2) Call get_crop_knowledge with the crop name to get all information.
3) If the crop name is invalid or not found, tell the user which crops
   are available and ask for clarification.
4) Read the tool output from BOTH the crop-specific files AND the
   General files, then write a concise answer summarising the most
   relevant guidance.
5) Do NOT invent facts. If files are missing or the crop is unresolved,
   briefly ask for clarification.

Varieties/Hybrids Rule:
- When asked for recommended varieties or hybrids, list names only.
- Give detailed descriptions only if explicitly asked.

Pests/Diseases Rule:
- When asked for pests or diseases, list names only.
- Give details or management practices only if explicitly asked.

Language Rule:
- Detect the language of the user's message and respond in that same
  language.

Style:
- Bullet points (1-5 based on need), no paragraphs, no headings, no links.
- Keep it factual, focused, and grounded in the text files only."""


def get_crop_knowledge(crop: str) -> str:
    """Get all knowledge about a specific oilseed crop including varieties,
    pests, diseases, management practices, and general agricultural info.

    Args:
        crop: The crop name (e.g., Sunflower, Groundnut, Soybean, Castor,
              Linseed, Niger, Rapeseed-mustard, Safflower, Sesame).

    Returns:
        JSON containing all crop-specific files and general agricultural
        information. If crop not found, returns available crops list.
    """
    resolved = knowledge_base.resolve_crop(crop)
    if not resolved:
        return json.dumps({
            "ok": False,
            "error": f"Could not match '{crop}'",
            "available_crops": knowledge_base.list_crops(),
        })
    
    crop_content = knowledge_base.get_crop_content(resolved)
    general_content = knowledge_base.get_general_content()

    result = {
        "ok": True,
        "crop": resolved,
        "crop_files": crop_content,
    }
    if general_content.get("ok"):
        result["general_files"] = general_content

    return json.dumps(result, default=str)


knowledge_agent = Agent(
    name="knowledge_agent",
    model=settings.KNOWLEDGE_MODEL,
    tools=[get_crop_knowledge],
    description=(
        "Answers questions about oilseed crops (Castor, Groundnut, Linseed, "
        "Niger, Rapeseed-mustard, Safflower, Sesame, Soybean, Sunflower) "
        "using authoritative local knowledge base files. Call this agent for "
        "any crop-related question: varieties, pests, diseases, management "
        "practices, soil, intercropping, etc."
    ),
    instruction=KNOWLEDGE_INSTRUCTION,
    generate_content_config=types.GenerateContentConfig(
        http_options=types.HttpOptions(
            retry_options=types.HttpRetryOptions(
                initial_delay=2,
                attempts=5,
            ),
        ),
    ),
)
