"""Knowledge functions for crop/agriculture questions using local .txt files."""

import json

from app.config import settings
from app.knowledge.file_reader import KnowledgeBase

knowledge_base = KnowledgeBase(settings.CROP_DIR)


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
