# Kisan Mitra - AI-Powered Agricultural Assistant

> **Gemini Live Agent Challenge Submission** - Live Agents Category

A real-time, multimodal AI assistant for Indian oilseed farmers, powered by Google's Gemini Live API and Agent Development Kit (ADK). Kisan Mitra ("Farmer's Friend") helps farmers with crop management through natural voice conversations, text chat, and visual crop disease detection.

## Quick Deploy

[![Run on Google Cloud](https://deploy.cloud.run/button.svg)](https://deploy.cloud.run)

> Click the button above to deploy your own instance of Kisan Mitra to Google Cloud Run in minutes. Requires a Google Cloud account with billing enabled.

## Demo

**Live Applications:**

| Deployment | URL | Region |
|------------|-----|--------|
| **Cloud Run** | https://icar-vision-backend-b3oagrv4ea-uc.a.run.app | us-central1 |
| **GCE (India)** | https://34.14.140.60 | asia-south1 (Mumbai) |

> Note: GCE uses a self-signed SSL certificate. Click "Advanced > Proceed" when prompted.

## Problem Statement

Indian oilseed farmers face challenges accessing timely agricultural advice:
- Limited access to agricultural experts in rural areas
- Language barriers (most farmers speak regional languages)
- Difficulty identifying crop diseases without expert knowledge
- Need for immediate, actionable guidance during critical crop stages

## Solution

Kisan Mitra is a **Live Agent** that farmers can interact with naturally through:

1. **Voice Conversations** - Speak in any language, get spoken responses
2. **Text Chat** - Type questions, receive text answers
3. **Video/Image Analysis** - Show crops via camera for disease detection

The agent leverages a curated knowledge base from ICAR-IIOR (Indian Institute of Oilseeds Research) covering 10 major oilseed crops.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              USER INTERFACE                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │   Landing   │→ │   Action    │→ │ AI Options  │→ │  Chat/Voice/Video   │ │
│  │   Screen    │  │   Screen    │  │   Screen    │  │     Interface       │ │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                    WebSocket (wss://)│ Audio/Text/Images
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         GOOGLE CLOUD RUN                                     │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                      FastAPI Backend                                   │  │
│  │  ┌─────────────────────────────────────────────────────────────────┐  │  │
│  │  │                    ADK Runner (Gemini Live)                      │  │  │
│  │  │  ┌─────────────────────────────────────────────────────────┐    │  │  │
│  │  │  │              ROOT AGENT (Live Audio + Vision)            │    │  │  │
│  │  │  │         gemini-live-2.5-flash-native-audio               │    │  │  │
│  │  │  │                                                          │    │  │  │
│  │  │  │    ┌────────────────────────────────────────────────┐   │    │  │  │
│  │  │  │    │            Direct Function Tools                │   │    │  │  │
│  │  │  │    │                                                 │   │    │  │  │
│  │  │  │    │  • get_crop_knowledge(crop)                     │   │    │  │  │
│  │  │  │    │  • get_disease_knowledge(crop)                  │   │    │  │  │
│  │  │  │    └──────────────┬──────────────────┬───────────────┘   │    │  │  │
│  │  │  └───────────────────┼──────────────────┼───────────────────┘    │  │  │
│  │  └──────────────────────┼──────────────────┼────────────────────────┘  │  │
│  └─────────────────────────┼──────────────────┼───────────────────────────┘  │
│                            ▼                  ▼                               │
│  ┌──────────────────────────────┐  ┌──────────────────────────┐              │
│  │    Crop Knowledge Base       │  │  Disease Knowledge Base  │              │
│  │    /crop/*.txt               │  │  /diseases/*/            │              │
│  │                              │  │  (text + images)         │              │
│  │  • Castor                    │  │                          │              │
│  │  • Groundnut                 │  │  • Sunflower diseases    │              │
│  │  • Linseed                   │  │  • Reference images      │              │
│  │  • Niger                     │  │                          │              │
│  │  • Rapeseed-mustard          │  │                          │              │
│  │  • Safflower                 │  │                          │              │
│  │  • Sesame                    │  │                          │              │
│  │  • Soybean                   │  │                          │              │
│  │  • Sunflower                 │  │                          │              │
│  └──────────────────────────────┘  └──────────────────────────┘              │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           VERTEX AI                                          │
│                    Gemini Live API (Streaming)                               │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Key Features

### Multimodal Interaction
- **Real-time Voice**: Bidirectional audio streaming with natural interruption handling
- **Text Chat**: Text-only mode for low-bandwidth scenarios
- **Vision Analysis**: Camera-based crop disease detection

### Direct Tools Architecture
- **Root Agent**: Gemini Live (`gemini-live-2.5-flash-native-audio`) - handles real-time voice/video/text with direct tool access
- **get_crop_knowledge()**: Queries crop knowledge base for varieties, pests, diseases, management practices
- **get_disease_knowledge()**: Retrieves disease symptoms, control measures, and reference images for visual comparison

> **Performance Optimized**: Direct function tools eliminate sub-agent overhead, reducing response time from ~5-8s to ~2-3s.

### Knowledge Grounding
- Curated knowledge base from ICAR-IIOR research
- 10 oilseed crops with detailed management practices
- Disease identification with reference images
- No hallucinations - responses grounded in authoritative sources

### Multilingual Support
- Automatic language detection and switching
- Responds in user's language (Hindi, Telugu, Tamil, Kannada, Marathi, English, etc.)
- Seamless mid-conversation language switching
- Code-mixed speech support (Hinglish, Tenglish)

### Language Deep Links

Direct URLs to open voice chat in a specific language:

| URL Path | Language | Greeting |
|----------|----------|----------|
| `/auto` | Auto-detect | (waits for user to speak) |
| `/hindi` | Hindi | नमस्ते, कृपया हिंदी में बात करें |
| `/telugu` | Telugu | నమస్కారం, దయచేసి తెలుగులో మాట్లాడండి |
| `/tamil` | Tamil | வணக்கம், தமிழில் பேசுங்கள் |
| `/kannada` | Kannada | ನಮಸ್ಕಾರ, ದಯವಿಟ್ಟು ಕನ್ನಡದಲ್ಲಿ ಮಾತನಾಡಿ |
| `/malayalam` | Malayalam | നമസ്കാരം, ദയവായി മലയാളത്തിൽ സംസാരിക്കുക |
| `/marathi` | Marathi | नमस्कार, कृपया मराठीत बोला |
| `/gujarati` | Gujarati | નમસ્તે, કૃપા કરીને ગુજરાતીમાં વાત કરો |
| `/bengali` | Bengali | নমস্কার, অনুগ্রহ করে বাংলায় কথা বলুন |
| `/odia` | Odia | ନମସ୍କାର, ଦୟାକରି ଓଡ଼ିଆରେ କଥା ହୁଅନ୍ତୁ |
| `/punjabi` | Punjabi | ਸਤ ਸ੍ਰੀ ਅਕਾਲ, ਕਿਰਪਾ ਕਰਕੇ ਪੰਜਾਬੀ ਵਿੱਚ ਗੱਲ ਕਰੋ |

**Usage:** Share `https://your-domain.com/telugu` to let users start directly in Telugu voice mode.

**Features:**
- Skips landing screens, goes directly to voice chat
- Auto-starts microphone (requests permission)
- Sends greeting in the specified language
- AI responds in that language immediately
- Users can still switch languages mid-conversation

## Technology Stack

| Component | Technology |
|-----------|------------|
| **AI Framework** | Google Agent Development Kit (ADK) |
| **Model** | Gemini Live 2.5 Flash Native Audio |
| **Backend** | FastAPI (Python 3.12) |
| **Hosting** | Google Cloud Run / Compute Engine |
| **AI Platform** | Vertex AI |
| **Real-time Communication** | WebSockets |
| **Frontend** | Vanilla HTML/CSS/JS (Mobile-first) |

## Project Structure

```
├── app/
│   ├── main.py                    # FastAPI app, WebSocket endpoints
│   ├── config.py                  # Settings and system instructions
│   ├── conversation_logger.py     # GCS conversation recording
│   ├── agents/
│   │   └── root_agent.py          # Root live agent with direct tools
│   ├── knowledge_agent/
│   │   └── agent.py               # get_crop_knowledge() function
│   ├── vision_assistant/
│   │   └── agent.py               # get_disease_knowledge() function
│   ├── knowledge/
│   │   └── file_reader.py         # Crop knowledge base loader
│   ├── disease_knowledge/
│   │   └── file_reader.py         # Disease knowledge base loader
│   └── static/
│       ├── index.html             # Main UI (landing + chat + voice + video)
│       └── test.html              # Developer test console
├── crop/                          # Crop knowledge base (10 crops)
│   ├── Castor/
│   ├── Groundnut/
│   ├── Sunflower/
│   └── ...
├── diseases/                      # Disease knowledge base
│   └── Sunflower/
│       ├── diseases.txt
│       └── images/
├── cloudrun/                      # Cloud Run deployment (us-central1)
│   ├── deploy.sh                  # One-command Cloud Run deployment
│   ├── app.json                   # Cloud Run Button configuration
│   ├── .env.example               # Cloud Run environment variables
│   └── README.md                  # Cloud Run deployment guide
├── gce/                           # Compute Engine deployment (asia-south1)
│   ├── deploy.sh                  # One-command GCE deployment
│   ├── .env.example               # GCE environment variables
│   └── README.md                  # GCE deployment guide
├── cloudbuild-cloudrun.yaml       # Cloud Build config for Cloud Run auto-deploy
├── cloudbuild-gce.yaml            # Cloud Build config for GCE auto-deploy
├── Dockerfile
└── requirements.txt
```

## Local Development

### Prerequisites

- Python 3.12+
- GCP project with Vertex AI API enabled
- `gcloud` CLI authenticated

### Setup

```bash
# Clone repository
git clone https://github.com/your-repo/kisan-mitra.git
cd kisan-mitra

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment (pick one based on your deployment target)
cp cloudrun/.env.example .env   # for Cloud Run / local dev
# cp gce/.env.example .env      # for Compute Engine (India region)
```

### Run Locally

```bash
uvicorn app.main:app --reload --port 8080
```

Open http://localhost:8080 in your browser.

### Test WebSocket

```bash
python test_ws.py
```

## Cloud Deployment

Two deployment options are available, each in its own self-contained folder:

| | Cloud Run | Compute Engine |
|---|---|---|
| **Folder** | [`cloudrun/`](cloudrun/) | [`gce/`](gce/) |
| **Region** | us-central1 | asia-south1 (Mumbai, India) |
| **Type** | Serverless (scales to zero) | Persistent VM (always on) |
| **Best for** | Demos, variable traffic | Production in India, low latency |
| **Guide** | [cloudrun/README.md](cloudrun/README.md) | [gce/README.md](gce/README.md) |

### Option 1: Cloud Run (Serverless)

```bash
export GOOGLE_CLOUD_PROJECT=your-project-id
./cloudrun/deploy.sh
```

See [cloudrun/README.md](cloudrun/README.md) for full instructions, one-click deploy button, and manual steps.

### Option 2: Compute Engine (Persistent VM in India)

```bash
export GOOGLE_CLOUD_PROJECT=your-project-id
./gce/deploy.sh
```

See [gce/README.md](gce/README.md) for full instructions including Vertex AI permissions, systemd setup, HTTPS with Nginx, and cleanup.

## Auto-Deploy (CI/CD)

This project uses **Cloud Build triggers** for automatic deployment on every push to `main`.

### How It Works

```
git push origin main
        │
        ▼
┌───────────────────────────────────────────────────────┐
│              GitHub (srimankatipally/ICAR_BackEnd)    │
└───────────────────────────────────────────────────────┘
        │
        ├──────────────────────┬────────────────────────┐
        ▼                      ▼                        │
┌─────────────────┐    ┌─────────────────┐              │
│ deploy-cloudrun │    │   deploy-gce    │              │
│    trigger      │    │    trigger      │              │
└────────┬────────┘    └────────┬────────┘              │
         │                      │                       │
         ▼                      ▼                       │
┌─────────────────┐    ┌─────────────────┐              │
│ Cloud Run       │    │ Build Image     │              │
│ --source deploy │    │ Push to         │              │
│ (~2-3 min)      │    │ Artifact Reg.   │              │
└─────────────────┘    └────────┬────────┘              │
                                │                       │
                                ▼                       │
                       ┌─────────────────┐              │
                       │ SSH into GCE VM │              │
                       │ Pull & Restart  │              │
                       │ (~4-5 min)      │              │
                       └─────────────────┘              │
```

### Build Configuration Files

| File | Target | Description |
|------|--------|-------------|
| `cloudbuild-cloudrun.yaml` | Cloud Run | Builds and deploys to Cloud Run (us-central1) |
| `cloudbuild-gce.yaml` | GCE | Builds image, pushes to Artifact Registry, SSHs into VM to deploy |

### Monitoring Builds

**Console:** https://console.cloud.google.com/cloud-build/builds?project=icarfinal

**CLI:**
```bash
# List recent builds
gcloud builds list --region=us-central1 --project=icarfinal --limit=5

# View build logs
gcloud builds log BUILD_ID --region=us-central1 --project=icarfinal
```

### Trigger Details

| Trigger | Branch | Config File | Duration |
|---------|--------|-------------|----------|
| `deploy-cloudrun` | `^main$` | `cloudbuild-cloudrun.yaml` | ~2-3 min |
| `deploy-gce` | `^main$` | `cloudbuild-gce.yaml` | ~4-5 min |

### Manual Trigger (without pushing)

```bash
# Trigger Cloud Run deploy manually
gcloud builds triggers run deploy-cloudrun --region=us-central1 --project=icarfinal --branch=main

# Trigger GCE deploy manually
gcloud builds triggers run deploy-gce --region=us-central1 --project=icarfinal --branch=main
```

### Multi-Stage Docker Build

The Dockerfile uses multi-stage builds for faster CI/CD:

```dockerfile
# Stage 1: Dependencies (cached layer)
FROM python:3.12-slim AS base
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: Application (rebuilt on code changes)
FROM base AS app
COPY . .
```

**Build Time Improvements:**

| Scenario | Before | After |
|----------|--------|-------|
| First build | ~3-4 min | ~3-4 min |
| Code change only | ~3-4 min | ~30-60 sec |
| requirements.txt change | ~3-4 min | ~3-4 min |

The GCE build uses `--cache-from` to pull the previous image and reuse cached layers.

## API Reference

### WebSocket Endpoints

| Endpoint | Mode | Description |
|----------|------|-------------|
| `/ws/{user_id}/{session_id}` | Audio | Voice/Video mode with audio responses |
| `/ws/text/{user_id}/{session_id}` | Text | Text-only mode |

### Session Isolation

Each WebSocket connection gets its own isolated ADK Runner and SessionService to prevent session mixing between users:

```
User A ──► Runner A ──► SessionService A ──► Gemini Session A
User B ──► Runner B ──► SessionService B ──► Gemini Session B
```

**Features:**
- Per-connection Runner instances (no shared state)
- Unique connection IDs in logs for debugging (e.g., `[a1b2c3d4]`)
- Cryptographically strong UUIDs for user and session IDs
- Complete isolation even on the same Cloud Run instance

### Client → Server Messages

| Type | Format | Description |
|------|--------|-------------|
| Binary | Raw PCM | Audio: 16kHz, 16-bit, mono |
| JSON | `{"type": "text", "text": "..."}` | Text message |
| JSON | `{"type": "image", "data": "<base64>", "mimeType": "image/jpeg"}` | Camera frame |

### Server → Client Events

| Field | Description |
|-------|-------------|
| `content.parts[].inlineData` | Audio response (PCM 24kHz) |
| `content.parts[].text` | Text response |
| `inputTranscription` | User speech transcription |
| `outputTranscription` | AI speech transcription |
| `turnComplete` | Response turn finished |
| `interrupted` | AI was interrupted |

### REST Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Main application UI |
| GET | `/test` | Developer test console |
| GET | `/health` | Health check |
| GET | `/config` | Public configuration |
| GET | `/{language}` | Language deep link (e.g., `/telugu`, `/hindi`, `/auto`) |

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GOOGLE_GENAI_USE_VERTEXAI` | Use Vertex AI backend | `TRUE` |
| `GOOGLE_CLOUD_PROJECT` | GCP project ID | (required) |
| `GOOGLE_CLOUD_LOCATION` | Vertex AI region | `us-central1` |
| `DEMO_AGENT_MODEL` | Live model | `gemini-live-2.5-flash-native-audio` |
| `CROP_DIR` | Crop knowledge path | `./crop` |
| `DISEASE_DIR` | Disease knowledge path | `./diseases` |
| `GCS_CONVERSATION_BUCKET` | GCS bucket for conversation recordings | (optional) |
| `RECORD_AUDIO` | Enable audio recording | `true` |
| `DEPLOYMENT_TAG` | Vertex AI tracking label (`cloudrun` or `gce`) | `unknown` |

## Hackathon Submission Details

### Category: Live Agents

This project qualifies for the **Live Agents** category because:

- **Real-time Interaction**: Users can speak naturally and receive immediate voice responses
- **Interruptible**: The agent handles interruptions gracefully using Gemini Live's native capabilities
- **Vision-enabled**: Camera integration for real-time crop disease detection
- **Contextual**: Maintains conversation context across turns

### Mandatory Requirements

| Requirement | Implementation |
|-------------|----------------|
| Gemini Model | `gemini-live-2.5-flash-native-audio` |
| Google GenAI SDK or ADK | ADK (Agent Development Kit) |
| Google Cloud Service | Cloud Run, Compute Engine, Vertex AI |



## Team

- **Sriman Katipally** - Developer
- **Nimesh CH** - Developer

## Data Usage & License

### Knowledge Base Data

The agricultural knowledge base data (crop information, disease data, and related content) included in this repository is the intellectual property of **ICAR-IIOR (Indian Council of Agricultural Research - Indian Institute of Oilseeds Research)**.

**Usage Rights:**
- **Sriman Katipally** and **Nimesh CH** have been granted complete rights to use this data for this project and related purposes.
- **Third parties** are NOT permitted to use, copy, distribute, or modify the knowledge base data without explicit written permission from ICAR-IIOR.
- All data usage is subject to ICAR-IIOR's terms and conditions.

For inquiries regarding data usage permissions, please contact ICAR-IIOR directly.

### Application Code

The application source code (excluding the knowledge base data) is available under the MIT License.

## Acknowledgments

- **ICAR-IIOR** (Indian Institute of Oilseeds Research) for providing the agricultural knowledge base and granting usage rights
- Google for the Gemini Live API and ADK
