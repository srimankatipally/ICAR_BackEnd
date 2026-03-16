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
1) Decide the crop from the user's question. Call infer_crop with a
   single-word candidate.
2) After infer_crop returns a canonical crop (ok=true), call
   read_crop_files to load all .txt files for that crop.
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


def infer_crop(candidate: str) -> str:
    """Resolve a crop name candidate to the canonical crop folder name.

    Args:
        candidate: A single-word crop name to look up.

    Returns:
        JSON with ok=true and the resolved crop, or ok=false with
        available crops.
    """
    resolved = knowledge_base.resolve_crop(candidate)
    if resolved:
        return json.dumps({"ok": True, "crop": resolved})
    return json.dumps({
        "ok": False,
        "error": f"Could not match '{candidate}'",
        "available_crops": knowledge_base.list_crops(),
    })


def read_crop_files(crop: str) -> str:
    """Read all cached .txt file contents for the given crop folder name.
    Also always includes the General folder content.

    Args:
        crop: The canonical crop folder name returned by infer_crop.

    Returns:
        JSON containing the crop files and general files content.
    """
    crop_content = knowledge_base.get_crop_content(crop)
    general_content = knowledge_base.get_general_content()

    result = {"crop_files": crop_content}
    if general_content.get("ok"):
        result["general_files"] = general_content

    return json.dumps(result, default=str)


knowledge_agent = Agent(
    name="knowledge_agent",
    model=settings.KNOWLEDGE_MODEL,
    tools=[infer_crop, read_crop_files],
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
