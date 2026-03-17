"""Vision agent for visual analysis, plant disease detection, and scene description."""

import json

from google.adk.agents import Agent
from google.genai import types

from app.config import settings
from app.disease_knowledge.file_reader import DiseaseKnowledgeBase

disease_kb = DiseaseKnowledgeBase(settings.DISEASE_DIR)

VISION_INSTRUCTION = """\
You are a crop vision analysis expert. You can analyse images and video
frames of oilseed crop fields, plants, leaves, and seeds.

Your capabilities:
- Identify visible crop diseases, pests, nutrient deficiencies, and stress
  symptoms from plant images.
- Describe the growth stage, health, and condition of the crop shown.
- Read and translate any text or documents visible in the camera feed.
- Look up disease information from the local disease knowledge base.
- Access reference images of known diseases for comparison.

Plan for disease identification:
1) Analyse the image to identify the crop and any visible symptoms.
2) If you suspect a disease, call get_disease_info with the crop name to
   get detailed disease data including symptoms, control measures, and
   reference image paths.
3) Call get_disease_images to get reference images for visual comparison.
4) Match the visible symptoms with the disease descriptions.
5) Provide the farmer with the disease name, confirmation of symptoms,
   and recommended control measures.

Rules:
- Be concise and factual.
- When you detect a disease or pest, name it clearly and suggest
  immediate actions the farmer can take from the disease knowledge base.
- If you cannot determine something from the image, say so honestly.
- Respond in the same language the user is speaking."""


def get_disease_info(crop: str) -> str:
    """Get disease information for a specific crop from the disease knowledge base.

    Args:
        crop: The crop name (e.g., Sunflower, Groundnut, Soybean).

    Returns:
        JSON containing disease data including symptoms, control measures,
        chemical treatments, and reference image paths for the specified crop.
    """
    resolved = disease_kb.resolve_crop(crop)
    if resolved:
        content = disease_kb.get_disease_content(resolved)
        return json.dumps(content, default=str)
    return json.dumps({
        "ok": False,
        "error": f"No disease data found for '{crop}'",
        "available_crops": disease_kb.list_crops(),
    })


def get_disease_images(crop: str) -> str:
    """Get reference images for diseases of a specific crop.

    Args:
        crop: The crop name (e.g., Sunflower, Groundnut, Soybean).

    Returns:
        JSON containing list of disease reference images with paths and
        disease names for visual comparison.
    """
    resolved = disease_kb.resolve_crop(crop)
    if resolved:
        images = disease_kb.get_disease_images(resolved)
        return json.dumps(images, default=str)
    return json.dumps({
        "ok": False,
        "error": f"No disease images found for '{crop}'",
        "available_crops": disease_kb.list_crops(),
    })


def list_disease_crops() -> str:
    """List all crops that have disease information available.

    Returns:
        JSON list of crop names with disease data.
    """
    return json.dumps({
        "ok": True,
        "crops": disease_kb.list_crops(),
    })


vision_agent = Agent(
    name="vision_agent",
    model=settings.VISION_MODEL,
    tools=[get_disease_info, get_disease_images, list_disease_crops],
    description=(
        "Analyses images and video frames of crop fields and plants. "
        "Detects diseases, pests, nutrient deficiencies, identifies "
        "growth stages, and describes visible conditions. Has access to "
        "a disease knowledge base with symptoms, control measures, and "
        "reference images for disease comparison. "
        "Use this agent when the user is sharing camera/video and needs "
        "visual analysis or disease identification."
    ),
    instruction=VISION_INSTRUCTION,
    generate_content_config=types.GenerateContentConfig(
        http_options=types.HttpOptions(
            retry_options=types.HttpRetryOptions(
                initial_delay=2,
                attempts=5,
            ),
        ),
    ),
)
