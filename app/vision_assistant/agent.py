"""Vision functions for disease detection using local knowledge base."""

import json

from app.config import settings
from app.disease_knowledge.file_reader import DiseaseKnowledgeBase

disease_kb = DiseaseKnowledgeBase(settings.DISEASE_DIR)


def get_disease_knowledge(crop: str) -> str:
    """Get all disease information for a specific crop including symptoms,
    control measures, chemical treatments, and reference image paths.

    Args:
        crop: The crop name (e.g., Sunflower, Groundnut, Soybean).

    Returns:
        JSON containing disease data, symptoms, control measures, and
        reference image paths. If crop not found, returns available crops.
    """
    resolved = disease_kb.resolve_crop(crop)
    if resolved:
        content = disease_kb.get_disease_content(resolved)
        images = disease_kb.get_disease_images(resolved)
        return json.dumps({
            "ok": True,
            "crop": resolved,
            "disease_info": content,
            "reference_images": images,
        }, default=str)
    return json.dumps({
        "ok": False,
        "error": f"No disease data found for '{crop}'",
        "available_crops": disease_kb.list_crops(),
    })
