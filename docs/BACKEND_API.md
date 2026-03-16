# ICAR Backend API -- Mapping Reference

This document describes how the React Native (Expo) mobile app communicates
with the ICAR Vision Backend. Use this as the definitive reference when
implementing WebSocket connections, audio streaming, camera capture, and
message handling in the mobile app.

## Backend URLs

| Environment | Base URL |
|-------------|----------|
| Production | `https://icar-vision-backend-56509313526.us-central1.run.app` |
| Local dev | `http://localhost:8080` |

## REST Endpoints

These are simple HTTP endpoints for health checks and configuration. No
authentication required.

### GET /health

```
Response: { "status": "ok", "app": "icar-vision" }
```

Use this to verify the backend is reachable before opening a WebSocket.

### GET /config

```
Response: {
  "model": "gemini-live-2.5-flash-native-audio",
  "gcp_location": "us-central1",
  "max_sessions": 10
}
```

Use this to display model info or check session limits.

---

## WebSocket Endpoint

### Connection URL

```
wss://{base_url}/ws/{user_id}/{session_id}
```

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| `user_id` | string | Persistent user identifier. Generate once with UUID v4, store in AsyncStorage. | `"usr-a1b2c3d4"` |
| `session_id` | string | Per-session identifier. Generate a new UUID v4 each time the user starts a session. | `"sess-e5f6g7h8"` |

### Connection Example (React Native)

```javascript
const userId = await AsyncStorage.getItem('user_id') || generateUUID();
const sessionId = generateUUID();
const ws = new WebSocket(`wss://icar-vision-backend-56509313526.us-central1.run.app/ws/${userId}/${sessionId}`);
ws.binaryType = 'arraybuffer';
```

Always set `binaryType = 'arraybuffer'` to receive audio as `ArrayBuffer`.

---

## Upstream Protocol (App to Server)

The app sends data to the server through the WebSocket. There are three
message types depending on the interaction mode.

### 1. Audio Data (Binary Frame)

Send raw microphone audio as binary WebSocket frames.

| Property | Value |
|----------|-------|
| Frame type | Binary |
| Format | Raw PCM |
| Sample rate | 16,000 Hz |
| Bit depth | 16-bit signed integer |
| Channels | 1 (mono) |
| Byte order | Little-endian |
| Chunk size | ~3,200 bytes (100ms of audio) |
| Send interval | Every ~100ms |

**Used in**: Audio mode, Video mode

```javascript
// Send audio chunk (ArrayBuffer of Int16 PCM samples)
ws.send(pcmArrayBuffer);
```

#### Recording with expo-av

```javascript
import { Audio } from 'expo-av';

const recording = new Audio.Recording();
await recording.prepareToRecordAsync({
  android: {
    extension: '.pcm',
    outputFormat: Audio.AndroidOutputFormat.DEFAULT,
    audioEncoder: Audio.AndroidAudioEncoder.DEFAULT,
    sampleRate: 16000,
    numberOfChannels: 1,
    bitRate: 256000,
  },
  ios: {
    extension: '.pcm',
    outputFormat: Audio.IOSOutputFormat.LINEARPCM,
    audioQuality: Audio.IOSAudioQuality.HIGH,
    sampleRate: 16000,
    numberOfChannels: 1,
    bitRate: 256000,
    linearPCMBitDepth: 16,
    linearPCMIsBigEndian: false,
    linearPCMIsFloat: false,
  },
  web: {},
});
await recording.startAsync();
```

Note: expo-av records to a file. You will need to read the file in chunks
and send them over WebSocket, OR use a lower-level audio API
(e.g., `expo-audio-stream` or a custom native module) to get real-time
PCM chunks. The recommended approach is to use a streaming audio library
that provides PCM buffers in real time.

### 2. Text Message (JSON Text Frame)

Send user-typed text as a JSON text frame.

```json
{
  "type": "text",
  "text": "Translate what you see in the camera"
}
```

**Used in**: Chat mode (primary), Audio/Video mode (optional, if text input is added)

```javascript
ws.send(JSON.stringify({ type: 'text', text: userMessage }));
```

### 3. Camera Frame (JSON Text Frame)

Send camera snapshots as base64-encoded JPEG in a JSON wrapper.

```json
{
  "type": "image",
  "data": "<base64-encoded JPEG bytes>",
  "mimeType": "image/jpeg"
}
```

| Property | Value |
|----------|-------|
| Format | JPEG |
| Resolution | 768x768 recommended |
| Quality | 0.7 (70%) |
| Interval | 1 frame per second |
| Encoding | Base64 string |

**Used in**: Video mode only

```javascript
// Capture from expo-camera ref
const photo = await cameraRef.current.takePictureAsync({
  base64: true,
  quality: 0.7,
  imageType: 'jpg',
  skipProcessing: true,
});

ws.send(JSON.stringify({
  type: 'image',
  data: photo.base64,
  mimeType: 'image/jpeg',
}));
```

Set up a 1-second interval to capture and send frames while in Video mode.

---

## Downstream Protocol (Server to App)

The server sends two types of WebSocket frames to the app.

### Binary Frames: Audio Response

When the AI speaks, the server sends raw PCM audio as binary WebSocket frames.

| Property | Value |
|----------|-------|
| Frame type | Binary (`ArrayBuffer`) |
| Format | Raw PCM |
| Sample rate | 24,000 Hz |
| Bit depth | 16-bit signed integer |
| Channels | 1 (mono) |
| Byte order | Little-endian |

**How to detect**: Check `event.data instanceof ArrayBuffer` in the `onmessage` handler.

**How to play**: Queue the PCM buffers and play them sequentially using
`expo-av`'s audio playback or the Web Audio API (for web testing).

```javascript
ws.onmessage = (event) => {
  if (event.data instanceof ArrayBuffer) {
    // Binary frame = PCM audio from AI
    enqueueAudioForPlayback(event.data);
    return;
  }
  // Text frame = JSON event
  const adkEvent = JSON.parse(event.data);
  handleEvent(adkEvent);
};
```

### Text Frames: JSON Events

All non-audio data arrives as JSON text frames. These are ADK Event objects.
Handle them based on their fields:

#### Input Transcription (what the user said)

```json
{
  "inputTranscription": {
    "text": "Hello, can you see this?",
    "finished": true
  },
  "partial": false
}
```

- Display as a user chat bubble.
- `partial: true` means the transcription is still being refined; update the existing bubble.
- `finished: true` means this is the final version.

#### Output Transcription (what the AI said)

```json
{
  "outputTranscription": {
    "text": "Yes, I can see a document. Would you like me to translate it?",
    "finished": true
  },
  "partial": false
}
```

- Display as an AI chat bubble.
- Same partial/finished logic as input transcription.

#### Text Content (Chat mode response)

```json
{
  "content": {
    "parts": [
      { "text": "The document appears to be in Spanish. Here's the translation..." }
    ]
  },
  "partial": true
}
```

- Display as an AI chat bubble.
- `partial: true` means more text is coming; append to the existing bubble.

#### Turn Complete

```json
{
  "turnComplete": true
}
```

- AI finished responding.
- Reset any "AI is speaking" indicators.
- Finalize any partial transcription bubbles.

#### Interrupted

```json
{
  "interrupted": true
}
```

- User interrupted the AI (started speaking while AI was talking).
- **Immediately stop audio playback** and clear the audio buffer.
- Mark the current AI bubble as interrupted (optional visual indicator).

#### Usage Metadata

```json
{
  "modelVersion": "gemini-live-2.5-flash-native-audio",
  "usageMetadata": {
    "promptTokenCount": 190,
    "candidatesTokenCount": 45,
    "totalTokenCount": 235
  }
}
```

- Optional: Display token usage for debugging.
- Can be ignored in production UI.

---

## Mode-to-Protocol Mapping

This table summarizes exactly what each mode sends and receives.

| | Audio Mode | Video Mode | Chat Mode |
|---|---|---|---|
| **Permissions** | Microphone | Microphone + Camera | None |
| **Upstream: Audio** | Binary PCM chunks (100ms) | Binary PCM chunks (100ms) | None |
| **Upstream: Camera** | None | JSON image frames (1 FPS) | None |
| **Upstream: Text** | None | None | JSON text messages |
| **Downstream: Audio** | Binary PCM (play it) | Binary PCM (play it) | None (ignore binary frames) |
| **Downstream: Transcripts** | JSON (display bubbles) | JSON (display bubbles) | JSON (display bubbles) |
| **Downstream: Text content** | Rare (usually audio) | Rare (usually audio) | Primary response format |
| **Audio Playback** | Yes | Yes | No |

---

## Session Lifecycle

### Connect

```
1. Generate user_id (persist in AsyncStorage) and session_id (new UUID per session)
2. GET /health to verify backend is reachable
3. Connect WebSocket: wss://{base}/ws/{user_id}/{session_id}
4. Set ws.binaryType = 'arraybuffer'
5. On open: start sending data per mode
```

### Active Session

```
6. Audio/Video mode: start mic recording, send PCM chunks as binary frames
7. Video mode: start camera capture, send JPEG frames as JSON every 1s
8. Chat mode: user types message, send as JSON text frame
9. Handle incoming events: play audio, display transcripts
10. Handle turnComplete: reset AI-speaking state
11. Handle interrupted: stop audio playback
```

### Disconnect

```
12. User taps "End Session" OR navigates away
13. Stop mic recording
14. Stop camera capture
15. Close WebSocket: ws.close()
16. Navigate back to Mode Selection
```

### Reconnection

```
On WebSocket close (unexpected):
  - Show "Reconnecting..." overlay
  - Wait 3 seconds
  - Reconnect with SAME user_id and session_id
  - Backend handles session resumption automatically
  - Retry up to 5 times, then show error with manual retry button
```

---

## Error Handling Reference

| Error | Detection | User Action |
|-------|-----------|-------------|
| Backend unreachable | `GET /health` fails or times out | Show "Server unavailable" with retry |
| WebSocket connection failed | `ws.onerror` fires | Show toast, auto-retry in 3s |
| WebSocket unexpected close | `ws.onclose` with code != 1000 | Show overlay, auto-reconnect |
| Mic permission denied | Permission API returns denied | Alert with "Open Settings" button |
| Camera permission denied | Permission API returns denied | Alert with "Open Settings" button |
| Session timeout (~10 min) | WebSocket closes gracefully | Auto-reconnect (ADK resumes server-side) |
| Large audio lag | Audio queue grows > 10 chunks | Skip old chunks, play latest |

---

## Quick Reference Card

```
Backend URL:     https://icar-vision-backend-56509313526.us-central1.run.app
WebSocket:       wss://{url}/ws/{user_id}/{session_id}
Health check:    GET /health
Config:          GET /config

SEND audio:      Binary frame, PCM 16kHz 16-bit mono LE, ~100ms chunks
SEND text:       JSON frame: {"type":"text","text":"..."}
SEND image:      JSON frame: {"type":"image","data":"<b64>","mimeType":"image/jpeg"}

RECV audio:      Binary frame, PCM 24kHz 16-bit mono LE
RECV transcript: JSON frame with inputTranscription or outputTranscription
RECV text:       JSON frame with content.parts[].text
RECV control:    JSON frame with turnComplete or interrupted
```
