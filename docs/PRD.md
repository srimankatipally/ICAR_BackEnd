# ICAR Mobile App -- Product Requirements Document

## Overview

ICAR is a React Native (Expo) mobile app that provides two ways to connect:
a WhatsApp-based support chat and a real-time AI assistant powered by Google
Gemini Live API. The AI assistant supports three interaction modes -- voice,
video, and text -- and communicates with a FastAPI backend deployed on Cloud
Run.

## Tech Stack

| Layer | Technology |
|-------|------------|
| Framework | React Native (Expo SDK 52+) |
| Navigation | expo-router or React Navigation 7 |
| Audio | expo-av (recording + playback) |
| Camera | expo-camera |
| WebSocket | React Native built-in WebSocket API |
| State | React Context or Zustand |
| UI | React Native core components + custom styling |

## App Flow

```
User opens app
  |
  v
[Splash Screen] -- auto-navigate after 2s
  |
  v
[Welcome Screen] -- greeting + two CTA buttons
  |
  +--> "Continue on WhatsApp"  --> Opens WhatsApp to +91 40 2459 8180
  |
  +--> "Continue with Gemini AI" --> [Mode Selection Screen]
                                        |
                                        +--> Audio  --+
                                        +--> Video  --+--> [Live Session Screen]
                                        +--> Chat   --+
                                                           |
                                                           +--> "End Session" --> back to Mode Selection
```

## Screens

### Screen 1: Splash

- Duration: 1.5--2 seconds, then auto-navigate to Welcome.
- Content:
  - App logo (centered)
  - App name "ICAR"
  - Optional tagline (e.g., "Your AI Vision Assistant")
- Background: Brand gradient or solid color.
- No user interaction required.

### Screen 2: Welcome

- Purpose: Greet the user and offer two communication paths.
- Content:
  - Greeting text: "Welcome to ICAR! How would you like to connect?"
  - Hero illustration or animated visual (optional).
  - Two buttons stacked vertically:

| Button | Label | Action |
|--------|-------|--------|
| Primary | "Continue on WhatsApp" | `Linking.openURL('https://wa.me/914024598180')` |
| Secondary | "Continue with Gemini AI" | Navigate to Mode Selection screen |

- WhatsApp button should have a WhatsApp icon.
- Gemini AI button should have a sparkle/AI icon.

### Screen 3: Mode Selection

- Purpose: Let the user choose their interaction mode.
- Header: "Choose your interaction mode"
- Three card-style buttons arranged vertically:

| Card | Icon | Title | Subtitle |
|------|------|-------|----------|
| Audio | Microphone | "Voice Chat" | "Talk with AI using your voice" |
| Video | Camera | "Video Chat" | "Show your camera and talk" |
| Chat | Keyboard | "Text Chat" | "Type messages to AI" |

- Back button (top-left) returns to Welcome.
- Each card navigates to Live Session with `mode` param.

### Screen 4: Live Session

This screen adapts based on the selected mode. It receives a `mode` parameter:
`'audio' | 'video' | 'chat'`.

#### Common Elements (all modes)

- **Connection status**: Green/red dot in header with "Connected"/"Connecting..."
- **End Session button**: Top-right, closes WebSocket and navigates back
- **Transcript panel**: Scrollable list of chat bubbles
  - User messages: right-aligned, distinct color
  - AI messages: left-aligned, distinct color
  - Auto-scrolls to newest message
- **AI speaking indicator**: Pulsing animation when AI is responding

#### Audio Mode Layout

```
+----------------------------------+
| [<Back]   Connected   [End]      |
+----------------------------------+
|                                  |
|     [Large animated waveform     |
|      or pulse indicator]         |
|                                  |
+----------------------------------+
|  Transcript panel                |
|  (scrollable chat bubbles)       |
|                                  |
+----------------------------------+
|        [Mic Toggle Button]       |
+----------------------------------+
```

- Mic button: Large, centered, toggle on/off with visual state change.
- Waveform: Animated ring or bars that react when user speaks or AI responds.
- No camera, no text input.

#### Video Mode Layout

```
+----------------------------------+
| [<Back]   Connected   [End]      |
+----------------------------------+
| +------------------------------+ |
| |                              | |
| |    Camera Preview            | |
| |    (live feed, rear camera)  | |
| |                              | |
| +------------------------------+ |
+----------------------------------+
|  Transcript panel                |
|  (compact, scrollable)           |
+----------------------------------+
| [Flip Cam]   [Mic Toggle]       |
+----------------------------------+
```

- Camera preview: Takes top half of screen.
- Camera flip button: Switches front/rear camera.
- Mic toggle: On by default, can mute.
- Camera frames captured at 1 FPS, sent as base64 JPEG.

#### Chat Mode Layout

```
+----------------------------------+
| [<Back]   Connected   [End]      |
+----------------------------------+
|                                  |
|  Transcript panel                |
|  (full height, scrollable        |
|   chat bubbles)                  |
|                                  |
+----------------------------------+
| [Text input field]     [Send]    |
+----------------------------------+
```

- Standard chat UI.
- Text input with send button.
- No mic, no camera.
- AI responses appear as text bubbles (no audio playback).

## Navigation Structure

```
Stack Navigator
  ├── SplashScreen          (no header)
  ├── WelcomeScreen         (no header)
  ├── ModeSelectScreen      (header with back button)
  └── LiveSessionScreen     (custom header with status + end button)
        params: { mode: 'audio' | 'video' | 'chat' }
```

## Permissions

| Permission | When Requested | Modes |
|------------|----------------|-------|
| Microphone | First time user selects Audio or Video mode | Audio, Video |
| Camera | First time user selects Video mode | Video |
| None | -- | Chat |

- Request permissions on mode selection tap, before navigating to Live Session.
- If denied, show explanation alert with option to open device Settings.
- Remember permission state; don't re-ask if already granted.

## Session Lifecycle

1. User selects a mode on Mode Selection screen.
2. App generates a `session_id` (UUID v4).
3. App retrieves or generates a persistent `user_id` (stored in AsyncStorage).
4. App navigates to Live Session screen.
5. On screen mount: connect WebSocket to `wss://{backend}/ws/{user_id}/{session_id}`.
6. On connect: begin sending data per mode (audio chunks, camera frames, or text).
7. On incoming events: play audio, display transcripts, handle interruptions.
8. On "End Session" tap or screen unmount: close WebSocket.
9. Navigate back to Mode Selection.

## Error Handling

| Error | User Experience |
|-------|-----------------|
| WebSocket disconnect | Show "Reconnecting..." overlay, auto-retry every 3 seconds |
| WebSocket error | Toast: "Connection error. Please try again." |
| Permission denied | Alert with explanation + "Open Settings" button |
| Session timeout (~10 min) | Transparent to user; backend handles session resumption |
| No internet | Show "No internet connection" screen with retry button |

## Non-Functional Requirements

- **Target platforms**: iOS 15+, Android 10+
- **Min Expo SDK**: 52
- **Audio latency**: Chunks sent every ~100ms for responsive voice interaction
- **Camera FPS**: 1 frame per second (not video streaming, just periodic snapshots)
- **Bundle size**: Keep under 30MB (avoid large native dependencies)
- **Offline**: Not supported; app requires active internet connection

## Future Enhancements (out of scope for v1)

- User authentication / login
- Chat history persistence
- Multi-language UI
- Push notifications
- In-app settings (voice selection, language preference)
- WhatsApp bot integration (server-side)
