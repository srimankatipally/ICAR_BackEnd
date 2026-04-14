"""Conversation logger that buffers transcripts + audio and uploads to GCS."""

from __future__ import annotations

import asyncio
import io
import json
import logging
import time
from datetime import datetime, timezone
from typing import Any

from google.cloud import storage

from app.config import settings

logger = logging.getLogger(__name__)

_gcs_client: storage.Client | None = None


def _get_gcs_client() -> storage.Client:
    global _gcs_client
    if _gcs_client is None:
        _gcs_client = storage.Client()
    return _gcs_client


class ConversationLogger:
    """Buffer conversation data in memory, then flush to GCS on session close."""

    def __init__(self, user_id: str, session_id: str, mode: str) -> None:
        self.enabled = bool(settings.GCS_CONVERSATION_BUCKET)
        self.bucket_name = settings.GCS_CONVERSATION_BUCKET
        self.record_audio = settings.RECORD_AUDIO

        self.user_id = user_id
        self.session_id = session_id
        self.mode = mode
        self.started_at = datetime.now(timezone.utc)

        self.messages: list[dict[str, Any]] = []
        self._user_audio = io.BytesIO() if self.record_audio else None
        self._ai_audio = io.BytesIO() if self.record_audio else None

    def _ts(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def log_user_text(self, text: str) -> None:
        if not self.enabled:
            return
        self.messages.append(
            {"role": "user", "type": "text", "text": text, "timestamp": self._ts()}
        )

    def log_user_transcription(self, text: str) -> None:
        if not self.enabled:
            return
        self.messages.append(
            {"role": "user", "type": "transcription", "text": text, "timestamp": self._ts()}
        )

    def log_ai_transcription(self, text: str) -> None:
        if not self.enabled:
            return
        self.messages.append(
            {"role": "ai", "type": "transcription", "text": text, "timestamp": self._ts()}
        )

    def log_ai_text(self, text: str) -> None:
        if not self.enabled:
            return
        self.messages.append(
            {"role": "ai", "type": "text", "text": text, "timestamp": self._ts()}
        )

    def log_user_audio(self, pcm_bytes: bytes) -> None:
        if not self.enabled or not self.record_audio or self._user_audio is None:
            return
        self._user_audio.write(pcm_bytes)

    def log_ai_audio(self, pcm_bytes: bytes) -> None:
        if not self.enabled or not self.record_audio or self._ai_audio is None:
            return
        self._ai_audio.write(pcm_bytes)

    async def flush(self) -> None:
        """Upload buffered data to GCS. Runs the blocking upload in a thread."""
        if not self.enabled:
            return
        if not self.messages and (
            not self._user_audio or self._user_audio.tell() == 0
        ):
            logger.info("ConversationLogger: nothing to flush (empty session)")
            return

        ended_at = datetime.now(timezone.utc)
        now = self.started_at

        prefix = f"{now.year}/{now.month:02d}/{now.day:02d}/{self.session_id}"

        metadata = {
            "session_id": self.session_id,
            "client_user_id": self.user_id,
            "mode": self.mode,
            "started_at": self.started_at.isoformat(),
            "ended_at": ended_at.isoformat(),
            "messages": self.messages,
        }

        loop = asyncio.get_event_loop()
        try:
            await loop.run_in_executor(
                None, self._upload_to_gcs, prefix, metadata
            )
            logger.info(
                "ConversationLogger: flushed session %s (%d messages, user_audio=%d bytes, ai_audio=%d bytes)",
                self.session_id,
                len(self.messages),
                self._user_audio.tell() if self._user_audio else 0,
                self._ai_audio.tell() if self._ai_audio else 0,
            )
        except Exception:
            logger.exception("ConversationLogger: failed to upload to GCS")

    def _upload_to_gcs(self, prefix: str, metadata: dict) -> None:
        client = _get_gcs_client()
        bucket = client.bucket(self.bucket_name)

        metadata_blob = bucket.blob(f"{prefix}/metadata.json")
        metadata_blob.upload_from_string(
            json.dumps(metadata, ensure_ascii=False, indent=2),
            content_type="application/json",
        )

        if self.record_audio and self._user_audio and self._user_audio.tell() > 0:
            self._user_audio.seek(0)
            user_audio_blob = bucket.blob(f"{prefix}/user_audio.pcm")
            user_audio_blob.upload_from_file(
                self._user_audio, content_type="audio/L16;rate=16000"
            )

        if self.record_audio and self._ai_audio and self._ai_audio.tell() > 0:
            self._ai_audio.seek(0)
            ai_audio_blob = bucket.blob(f"{prefix}/ai_audio.pcm")
            ai_audio_blob.upload_from_file(
                self._ai_audio, content_type="audio/L16;rate=24000"
            )


def list_recent_sessions(limit: int = 50) -> list[dict[str, Any]]:
    """List recent conversation sessions from GCS, sorted newest first.

    Scans metadata.json blobs under the date-based prefix structure.
    Runs synchronously (to be called from an async endpoint via run_in_executor).
    """
    if not settings.GCS_CONVERSATION_BUCKET:
        return []

    client = _get_gcs_client()
    bucket = client.bucket(settings.GCS_CONVERSATION_BUCKET)

    sessions: list[dict[str, Any]] = []
    blobs = bucket.list_blobs(match_glob="**/metadata.json")

    for blob in blobs:
        try:
            content = blob.download_as_text()
            meta = json.loads(content)
            sessions.append(
                {
                    "session_id": meta.get("session_id", ""),
                    "client_user_id": meta.get("client_user_id", ""),
                    "mode": meta.get("mode", ""),
                    "started_at": meta.get("started_at", ""),
                    "ended_at": meta.get("ended_at", ""),
                    "message_count": len(meta.get("messages", [])),
                    "gcs_path": f"gs://{settings.GCS_CONVERSATION_BUCKET}/{blob.name.rsplit('/metadata.json', 1)[0]}",
                }
            )
        except Exception:
            logger.warning("Failed to parse metadata blob: %s", blob.name)

    sessions.sort(key=lambda s: s.get("started_at", ""), reverse=True)
    return sessions[:limit]
