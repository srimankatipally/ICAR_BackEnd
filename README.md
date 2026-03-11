# ICAR Vision Backend

Real-time visual and voice assistant backend powered by the Google Agent Development Kit (ADK) and the Gemini Live API. Deployed on Cloud Run, authenticated to Vertex AI via IAM -- no API keys needed.

## What it does

A user opens the mobile app, grants camera and microphone access, and starts talking. The backend:

1. Receives live audio (PCM) and camera frames (JPEG) over a WebSocket
2. Streams them to Gemini via ADK's Live API Toolkit
3. Returns AI voice responses, transcriptions, and text in real time

Key features: scene description, document translation, visual Q&A, web search grounding.

## Architecture

```
React Native App  <--WebSocket-->  FastAPI + ADK (Cloud Run)  <--Live API-->  Vertex AI (Gemini)
                                         |
                                   IAM service account
                                   (roles/aiplatform.user)
```

## Project structure

```
app/
  __init__.py
  main.py                  # FastAPI app, WebSocket endpoint, upstream/downstream tasks
  config.py                # Settings (GCP project, model, CORS, system prompt)
  vision_assistant/
    __init__.py
    agent.py               # ADK Agent with google_search tool
Dockerfile                 # Python 3.12 slim, port 8080
deploy.sh                  # One-command Cloud Run deployment
requirements.txt
.env.example
test_ws.py                 # WebSocket test client
```

## Local development

### Prerequisites

- Python 3.12+
- A GCP project with the Vertex AI API enabled
- `gcloud` CLI installed and authenticated (`gcloud auth application-default login`)

### Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Edit .env with your GCP project ID
```

### Run

```bash
uvicorn app.main:app --reload --port 8080
```

### Test

```bash
pip install websockets
python test_ws.py
```

## Cloud Run deployment

```bash
export GOOGLE_CLOUD_PROJECT=your-project-id
export GOOGLE_CLOUD_LOCATION=us-central1

./deploy.sh
```

The script will:
1. Enable required APIs (Vertex AI, Cloud Run, Cloud Build)
2. Create a service account with `roles/aiplatform.user`
3. Build and deploy the container to Cloud Run
4. Print the service URL

## WebSocket protocol

Connect to: `wss://<service-url>/ws/{user_id}/{session_id}`

### Client to server (upstream)

| Frame type | Format | Description |
|---|---|---|
| Binary | Raw PCM bytes | Audio: 16kHz, 16-bit, mono |
| Text (JSON) | `{"type": "text", "text": "..."}` | Text command |
| Text (JSON) | `{"type": "image", "data": "<base64>", "mimeType": "image/jpeg"}` | Camera frame |

### Server to client (downstream)

ADK `Event` objects serialized as JSON. Key fields:

| Field | Meaning |
|---|---|
| `content.parts[].inlineData` | Audio response (base64 PCM 24kHz) |
| `content.parts[].text` | Text response |
| `inputTranscription` | What the user said (speech-to-text) |
| `outputTranscription` | What the AI said (speech-to-text) |
| `interrupted` | AI was interrupted -- clear audio buffer |
| `turnComplete` | AI finished a response turn |
| `partial` | Intermediate chunk, more coming |

## REST endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Health check |
| GET | `/config` | Public configuration (model, location) |

## Environment variables

| Variable | Description | Default |
|---|---|---|
| `GOOGLE_GENAI_USE_VERTEXAI` | Use Vertex AI backend | `TRUE` |
| `GOOGLE_CLOUD_PROJECT` | GCP project ID | (required) |
| `GOOGLE_CLOUD_LOCATION` | Vertex AI region | `us-central1` |
| `DEMO_AGENT_MODEL` | Gemini model ID | `gemini-live-2.5-flash-native-audio` |
