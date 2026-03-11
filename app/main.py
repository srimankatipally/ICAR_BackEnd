"""FastAPI backend for real-time vision + voice assistant using ADK Gemini Live API Toolkit."""

import asyncio
import base64
import json
import logging
import warnings
from pathlib import Path

from dotenv import load_dotenv

# Load .env BEFORE any app imports so config.py picks up the env vars
load_dotenv(Path(__file__).parent.parent / ".env")

from fastapi import FastAPI, WebSocket, WebSocketDisconnect  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.responses import FileResponse  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402
from google.adk.agents.live_request_queue import LiveRequestQueue  # noqa: E402
from google.adk.agents.run_config import RunConfig, StreamingMode  # noqa: E402
from google.adk.runners import Runner  # noqa: E402
from google.adk.sessions import InMemorySessionService  # noqa: E402
from google.genai import types  # noqa: E402

from app.config import settings  # noqa: E402
from app.vision_assistant import agent  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)
warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")

APP_NAME = "icar-vision"

# --- Phase 1: Application Initialization (once at startup) ---

app = FastAPI(title="ICAR Vision Backend", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")

session_service = InMemorySessionService()
runner = Runner(app_name=APP_NAME, agent=agent, session_service=session_service)


# --- REST Endpoints ---


@app.get("/")
async def root():
    return FileResponse(static_dir / "index.html")


@app.get("/health")
async def health():
    return {"status": "ok", "app": APP_NAME}


@app.get("/config")
async def public_config():
    return {
        "model": settings.GEMINI_MODEL,
        "gcp_location": settings.GCP_LOCATION,
        "max_sessions": settings.MAX_SESSIONS,
    }


# --- WebSocket Endpoint ---


@app.websocket("/ws/{user_id}/{session_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    user_id: str,
    session_id: str,
) -> None:
    """Bidirectional streaming endpoint.

    Audio is sent as binary WebSocket frames (raw PCM 16kHz 16-bit mono).
    Text and images are sent as JSON text frames.
    """
    logger.info(
        "WebSocket connection request: user_id=%s, session_id=%s",
        user_id,
        session_id,
    )
    await websocket.accept()
    logger.info("WebSocket connection accepted")

    # --- Phase 2: Session Initialization ---

    is_native_audio = "native-audio" in settings.GEMINI_MODEL.lower()

    if is_native_audio:
        run_config = RunConfig(
            streaming_mode=StreamingMode.BIDI,
            response_modalities=["AUDIO"],
            input_audio_transcription=types.AudioTranscriptionConfig(),
            output_audio_transcription=types.AudioTranscriptionConfig(),
            session_resumption=types.SessionResumptionConfig(),
        )
    else:
        run_config = RunConfig(
            streaming_mode=StreamingMode.BIDI,
            response_modalities=["TEXT"],
            session_resumption=types.SessionResumptionConfig(),
        )

    session = await session_service.get_session(
        app_name=APP_NAME, user_id=user_id, session_id=session_id
    )
    if not session:
        await session_service.create_session(
            app_name=APP_NAME, user_id=user_id, session_id=session_id
        )

    live_request_queue = LiveRequestQueue()

    # --- Phase 3: Active Session (concurrent bidirectional communication) ---

    async def upstream_task() -> None:
        """Receive messages from the client WebSocket and forward to ADK."""
        while True:
            message = await websocket.receive()

            if "bytes" in message:
                audio_data = message["bytes"]
                logger.debug("Received audio chunk: %d bytes", len(audio_data))
                audio_blob = types.Blob(
                    mime_type="audio/pcm;rate=16000", data=audio_data
                )
                live_request_queue.send_realtime(audio_blob)

            elif "text" in message:
                text_data = message["text"]
                logger.debug("Received text frame: %s", text_data[:120])

                try:
                    json_message = json.loads(text_data)
                except json.JSONDecodeError:
                    logger.warning("Invalid JSON from client, ignoring")
                    continue

                msg_type = json_message.get("type")

                if msg_type == "text":
                    content = types.Content(
                        parts=[types.Part(text=json_message["text"])]
                    )
                    live_request_queue.send_content(content)

                elif msg_type == "image":
                    image_data = base64.b64decode(json_message["data"])
                    mime_type = json_message.get("mimeType", "image/jpeg")
                    logger.debug(
                        "Sending image: %d bytes, type: %s",
                        len(image_data),
                        mime_type,
                    )
                    image_blob = types.Blob(mime_type=mime_type, data=image_data)
                    live_request_queue.send_realtime(image_blob)

                else:
                    logger.warning("Unknown message type: %s", msg_type)

    async def downstream_task() -> None:
        """Receive ADK events from run_live() and forward to the client WebSocket.

        Audio inline_data is extracted and sent as binary WS frames for
        efficiency.  A small JSON header frame is sent first so the client
        knows the binary frame that follows is audio.  All other events are
        sent as JSON text frames.
        """
        event_count = 0
        audio_count = 0
        async for event in runner.run_live(
            user_id=user_id,
            session_id=session_id,
            live_request_queue=live_request_queue,
            run_config=run_config,
        ):
            event_count += 1

            # Fast path: extract audio inline_data and send as binary
            has_audio = False
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.inline_data and part.inline_data.data:
                        audio_count += 1
                        has_audio = True
                        raw_bytes = part.inline_data.data
                        if isinstance(raw_bytes, str):
                            raw_bytes = base64.b64decode(raw_bytes)
                        await websocket.send_bytes(raw_bytes)

            # Send non-audio events (or events that also have text) as JSON
            if not has_audio:
                event_json = event.model_dump_json(
                    exclude_none=True, by_alias=True
                )
                await websocket.send_text(event_json)
            else:
                # For audio events, still send metadata (transcriptions etc.)
                # but strip the heavy inline_data to keep it small
                try:
                    stripped = event.model_copy(deep=True)
                    if stripped.content and stripped.content.parts:
                        new_parts = []
                        for p in stripped.content.parts:
                            if p.inline_data and p.inline_data.data:
                                continue
                            new_parts.append(p)
                        if new_parts:
                            stripped.content.parts = new_parts
                            stripped_json = stripped.model_dump_json(
                                exclude_none=True, by_alias=True
                            )
                            await websocket.send_text(stripped_json)
                except Exception:
                    pass

        logger.info(
            "run_live finished: %d events total, %d audio events",
            event_count,
            audio_count,
        )

    try:
        await asyncio.gather(upstream_task(), downstream_task())
    except WebSocketDisconnect:
        logger.info("Client disconnected: user_id=%s, session_id=%s", user_id, session_id)
    except Exception as e:
        logger.error("Streaming error: %s", e, exc_info=True)
    finally:
        # --- Phase 4: Session Termination ---
        live_request_queue.close()
        logger.info("Session closed: user_id=%s, session_id=%s", user_id, session_id)
