import json
import asyncio
from fastapi import WebSocket, WebSocketDisconnect
from .asr import handle_audio_chunk, finalize_transcript
from .orchestrator import process_final_transcript
from .event_streamer import (
    PartialTranscriptEvent,
    FinalTranscriptEvent,
    LLMTokenEvent,
    StatusUpdateEvent,
    ErrorEvent,
    serialize_event,
)
from .auth import decode_token

async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    user_id: str | None = None
    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
            except json.JSONDecodeError:
                await websocket.send_text(serialize_event(ErrorEvent(message="Invalid JSON")))
                continue

            msg_type = msg.get("type")
            if msg_type == "auth":
                token = msg.get("token")
                if not token:
                    await websocket.send_text(serialize_event(ErrorEvent(message="Missing token")))
                    continue
                try:
                    token_data = decode_token(token)
                    user_id = token_data.user_id
                    await websocket.send_text(serialize_event(StatusUpdateEvent(status="authenticated")))
                except Exception as e:
                    await websocket.send_text(serialize_event(ErrorEvent(message=str(e))))
                    continue
            elif user_id is None:
                await websocket.send_text(serialize_event(ErrorEvent(message="Unauthenticated. Send auth message first.")))
                continue
            elif msg_type == "audio":
                chunk = msg.get("chunk", "")
                await handle_audio_chunk(user_id, chunk)
                await websocket.send_text(serialize_event(PartialTranscriptEvent(text=chunk)))
            elif msg_type == "end":
                transcript = await finalize_transcript(user_id)
                await websocket.send_text(serialize_event(FinalTranscriptEvent(text=transcript)))
                
                # Stream results from Gemini
                async for token_event in process_final_transcript(user_id, transcript):
                    await websocket.send_text(serialize_event(token_event))
                
                await websocket.send_text(serialize_event(StatusUpdateEvent(status="completed")))
            else:
                await websocket.send_text(serialize_event(ErrorEvent(message="Unknown message type")))
    except WebSocketDisconnect:
        # Cleanup if needed
        pass
