# Kisan Mitra - AI-Powered Agricultural Assistant

> **Gemini Live Agent Challenge Submission** - Live Agents Category

A real-time, multimodal AI assistant for Indian oilseed farmers, powered by Google's Gemini Live API and Agent Development Kit (ADK). Kisan Mitra ("Farmer's Friend") helps farmers with crop management through natural voice conversations, text chat, and visual crop disease detection.

## Quick Deploy

[![Run on Google Cloud](https://deploy.cloud.run/button.svg)](https://deploy.cloud.run)

> Click the button above to deploy your own instance of Kisan Mitra to Google Cloud Run in minutes. Requires a Google Cloud account with billing enabled.

## Demo

**Live Application:** https://icar-vision-backend-ykitwyw32a-uc.a.run.app/

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
├── cloudrun/                     # Cloud Run deployment (us-central1)
│   ├── deploy.sh                 # One-command Cloud Run deployment
│   ├── app.json                  # Cloud Run Button configuration
│   ├── .env.example              # Cloud Run environment variables
│   └── README.md                 # Cloud Run deployment guide
├── gce/                          # Compute Engine deployment (asia-south1)
│   ├── deploy.sh                 # One-command GCE deployment
│   ├── .env.example              # GCE environment variables
│   └── README.md                 # GCE deployment guide
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

## API Reference

### WebSocket Endpoints

| Endpoint | Mode | Description |
|----------|------|-------------|
| `/ws/{user_id}/{session_id}` | Audio | Voice/Video mode with audio responses |
| `/ws/text/{user_id}/{session_id}` | Text | Text-only mode |

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

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GOOGLE_GENAI_USE_VERTEXAI` | Use Vertex AI backend | `TRUE` |
| `GOOGLE_CLOUD_PROJECT` | GCP project ID | (required) |
| `GOOGLE_CLOUD_LOCATION` | Vertex AI region | `us-central1` |
| `DEMO_AGENT_MODEL` | Live model | `gemini-live-2.5-flash-native-audio` |
| `CROP_DIR` | Crop knowledge path | `./crop` |
| `DISEASE_DIR` | Disease knowledge path | `./diseases` |

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
