"""In-memory disease knowledge base loaded from disease .txt files and images."""

import logging
from difflib import SequenceMatcher
from pathlib import Path

logger = logging.getLogger(__name__)


class DiseaseKnowledgeBase:
    def __init__(self, disease_dir: str):
        self._disease_dir = Path(disease_dir)
        self._cache: dict[str, dict] = {}
        self._crops: list[str] = []
        self.load()

    def load(self):
        """Read all crop disease folders and cache .txt contents and images in memory."""
        if not self._disease_dir.exists():
            logger.error("Disease directory not found: %s", self._disease_dir)
            return

        self._cache.clear()
        self._crops.clear()

        for folder in sorted(self._disease_dir.iterdir()):
            if not folder.is_dir():
                continue

            crop_name = folder.name
            files = []
            images = []

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

            images_dir = folder / "images"
            if images_dir.exists():
                for img_file in sorted(images_dir.glob("*.jpeg")) + sorted(images_dir.glob("*.jpg")) + sorted(images_dir.glob("*.png")):
                    disease_name = img_file.stem.replace("_", " ").title()
                    images.append({
                        "path": str(img_file),
                        "filename": img_file.name,
                        "disease_name": disease_name,
                    })

            self._cache[crop_name] = {"files": files, "images": images}
            self._crops.append(crop_name)

        total_images = sum(len(v["images"]) for v in self._cache.values())
        logger.info(
            "Disease knowledge base loaded: %d crops, %d text files, %d images",
            len(self._crops),
            sum(len(v["files"]) for v in self._cache.values()),
            total_images,
        )

    def list_crops(self) -> list[str]:
        """Return available crop folder names with disease data."""
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

    def get_disease_content(self, crop: str) -> dict:
        """Return cached disease file contents for a crop."""
        if crop not in self._cache:
            return {"ok": False, "crop": crop, "error": "Crop disease data not found"}
        data = self._cache[crop]
        return {
            "ok": True,
            "crop": crop,
            "files": [{"path": f["path"], "content": f["content"]} for f in data["files"]],
            "images": data.get("images", []),
        }

    def get_disease_images(self, crop: str) -> dict:
        """Return list of disease images for a crop."""
        if crop not in self._cache:
            return {"ok": False, "crop": crop, "error": "Crop disease data not found"}
        data = self._cache[crop]
        return {
            "ok": True,
            "crop": crop,
            "images": data.get("images", []),
        }

    def get_all_diseases(self) -> dict:
        """Return all disease data for all crops."""
        all_data = {}
        for crop in self._crops:
            all_data[crop] = self.get_disease_content(crop)
        return all_data
