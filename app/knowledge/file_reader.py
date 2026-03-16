"""In-memory knowledge base loaded from crop .txt files."""

import logging
from difflib import SequenceMatcher
from pathlib import Path

logger = logging.getLogger(__name__)


class KnowledgeBase:
    def __init__(self, crop_dir: str):
        self._crop_dir = Path(crop_dir)
        self._cache: dict[str, dict] = {}
        self._crops: list[str] = []
        self.load()

    def load(self):
        """Read all crop folders and cache .txt contents in memory."""
        if not self._crop_dir.exists():
            logger.error("Crop directory not found: %s", self._crop_dir)
            return

        self._cache.clear()
        self._crops.clear()

        for folder in sorted(self._crop_dir.iterdir()):
            if not folder.is_dir():
                continue

            crop_name = folder.name
            files = []
            for txt_file in sorted(folder.glob("*.txt")):
                try:
                    content = txt_file.read_text(encoding="utf-8", errors="replace")
                    files.append({
                        "path": str(txt_file),
                        "name": txt_file.name,
                        "content": content,
                    })
                except Exception as e:
                    logger.warning("Failed to read %s: %s", txt_file, e)

            self._cache[crop_name] = {"files": files}
            self._crops.append(crop_name)

        logger.info(
            "Knowledge base loaded: %d crops, %d total files",
            len(self._crops),
            sum(len(v["files"]) for v in self._cache.values()),
        )

    def list_crops(self) -> list[str]:
        """Return available crop folder names."""
        return list(self._crops)

    def resolve_crop(self, candidate: str) -> str | None:
        """Fuzzy match a candidate name to an actual crop folder.

        Returns None if best match ratio < 0.75.
        """
        if not candidate:
            return None

        candidate_lower = candidate.strip().lower()

        for crop in self._crops:
            if crop.lower() == candidate_lower:
                return crop

        best_match = None
        best_ratio = 0.0
        for crop in self._crops:
            ratio = SequenceMatcher(None, candidate_lower, crop.lower()).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_match = crop

        if best_ratio >= 0.75:
            return best_match
        return None

    def get_crop_content(self, crop: str) -> dict:
        """Return cached file contents for a crop."""
        if crop not in self._cache:
            return {"ok": False, "crop": crop, "error": "Crop not found"}
        data = self._cache[crop]
        return {
            "ok": True,
            "crop": crop,
            "files": [{"path": f["path"], "content": f["content"]} for f in data["files"]],
        }

    def get_general_content(self) -> dict:
        """Return cached General/ folder content."""
        return self.get_crop_content("General")
