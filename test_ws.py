"""Simple WebSocket test client for the ICAR Vision Backend.

Usage:
    pip install websockets
    python test_ws.py                           # default localhost
    python test_ws.py wss://your-cloud-run-url  # test deployed instance
"""

import asyncio
import json
import sys

try:
    import websockets
except ImportError:
    print("Install websockets first:  pip install websockets")
    sys.exit(1)

BASE_URL = sys.argv[1] if len(sys.argv) > 1 else "ws://localhost:8080"
USER_ID = "test-user"
SESSION_ID = "test-session-001"
WS_URL = f"{BASE_URL}/ws/{USER_ID}/{SESSION_ID}"


async def main():
    print(f"Connecting to {WS_URL} ...")
    async with websockets.connect(WS_URL) as ws:
        print("Connected! Sending text message...")

        msg = json.dumps({"type": "text", "text": "Hello! What can you do?"})
        await ws.send(msg)
        print(f"Sent: {msg}")

        print("\nWaiting for events (Ctrl+C to stop):\n")
        try:
            async for raw in ws:
                event = json.loads(raw)

                if event.get("input_transcription"):
                    print(f"  [USER TRANSCRIPT] {event['input_transcription']}")
                elif event.get("output_transcription"):
                    print(f"  [MODEL TRANSCRIPT] {event['output_transcription']}")
                elif event.get("content", {}).get("parts"):
                    for part in event["content"]["parts"]:
                        if "text" in part:
                            print(f"  [TEXT] {part['text']}")
                        elif "inlineData" in part:
                            data_len = len(part["inlineData"].get("data", ""))
                            print(f"  [AUDIO] {data_len} bytes base64")
                elif event.get("interrupted"):
                    print("  [INTERRUPTED]")

                if event.get("turnComplete"):
                    print("  [TURN COMPLETE]\n")

        except KeyboardInterrupt:
            print("\nDisconnecting...")


if __name__ == "__main__":
    asyncio.run(main())
