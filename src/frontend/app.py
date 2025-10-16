import chainlit as cl
import httpx
import uuid
import json
import asyncio
import websockets
from websockets.exceptions import ConnectionClosed, WebSocketException
# TODO: proper ws exception handling

# TODO: move settings.py with these
BACKEND_URL = "http://localhost:8000"
WS_URL = "ws://localhost:8000/ws"

# TODO chainlid.md used as 'homepage'


# Backend health check

async def check_backend_health() -> bool:
    """Check if backend is healthy."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{BACKEND_URL}/api/v1/health")
            return response.status_code == 200
    except Exception as e:
        print(f"Health check failed: {e}")
        return False


# WebSocket connection manager (per user session)
class WSManager:
    """Manages a single persistent websocket connection."""

    def __init__(self, uri: str, on_message):
        self.uri = uri
        self.on_message = on_message  # async callback
        self._ws = None
        self._send_q = asyncio.Queue()
        self._stopped = asyncio.Event()
        self._task = None

    async def start(self):
        if not self._task:
            self._task = asyncio.create_task(self._run())

    async def stop(self):
        """Stop background tasks and close connection."""
        self._stopped.set()
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        if self._ws:
            try:
                await self._ws.close()
            except Exception:
                pass
        self._ws = None
        print("WebSocket manager stopped")

    async def send(self, payload: dict):
        """Queue a message to send."""
        await self._send_q.put(json.dumps(payload))

    # Internals
    async def _connect(self):
        print(f"Connecting to WebSocket: {self.uri}")
        return await websockets.connect(
            self.uri, ping_interval=20, ping_timeout=20, close_timeout=10
        )

    async def _run(self):
        """Reconnect loop: restarts reader/writer on failure."""
        backoff = 1
        while not self._stopped.is_set():
            try:
                self._ws = await self._connect()
                print("ws connected")
                backoff = 1

                # spawn reader/writer tasks
                reader = asyncio.create_task(self._reader())
                writer = asyncio.create_task(self._writer())
                done, pending = await asyncio.wait(
                    {reader, writer}, return_when=asyncio.FIRST_EXCEPTION
                )

                for t in pending:
                    t.cancel()

                # propagate errors (to trigger reconnect)
                for t in done:
                    t.result()

            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"WebSocket error: {e}")
            finally:
                if self._ws:
                    try:
                        await self._ws.close()
                    except Exception:
                        pass
                    self._ws = None

            if self._stopped.is_set():
                break

            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 5)  # capped backoff

    async def _reader(self):
        """Continuously receive messages and forward them to handler."""
        assert self._ws is not None
        while not self._stopped.is_set():
            try:
                msg = await self._ws.recv()
                await self.on_message(msg)
            except ConnectionClosed:
                print("🔌 Connection closed (reader)")
                break
            except Exception as e:
                print(f"Reader error: {e}")
                break

    async def _writer(self):
        """Continuously send queued messages."""
        assert self._ws is not None
        while not self._stopped.is_set():
            data = await self._send_q.get()
            try:
                await self._ws.send(data)
            except ConnectionClosed:
                print("Connection closed (writer)")
                await self._send_q.put(data)  # requeue for retry
                break
            except Exception as e:
                print(f"Writer error: {e}")
                break


# ---------------------------------------------------------------------------
# Chainlit handlers
# ---------------------------------------------------------------------------

@cl.on_chat_start
async def start_chat():
    """Initialize the chat session and establish WebSocket manager."""
    if not await check_backend_health():
        # TODO: update this message. "We're having issues" kind of thing..
        await cl.Message(
            content="Backend service is not available. Please ensure the FastAPI server is running."
        ).send()
        return

    session_id = str(uuid.uuid4())
    cl.user_session.set("session_id", session_id)
    uri = f"{WS_URL}/{session_id}"

    async def on_backend_message(raw: str):
        """Callback for messages coming from backend."""
        msg = cl.user_session.get("active_msg")
        if not msg:
            return
        try:
            data = json.loads(raw)
        except Exception:
            data = {"type": "token", "content": raw}

        t = data.get("type")
        content = data.get("content", "")

        if t == "token":
            await msg.stream_token(content)
        elif t == "end":
            await msg.update()
        elif t == "error":
            await cl.ErrorMessage(content=content).send()

    manager = WSManager(uri, on_backend_message)
    cl.user_session.set("ws_manager", manager)
    await manager.start()

    await cl.Message(content="I'm an expert on ADHD medications. Ask me anything about it!").send()


@cl.on_message
async def on_message(message: cl.Message):
    """Handle user input by sending to backend through manager."""
    manager: WSManager = cl.user_session.get("ws_manager")
    if not manager:
        # TODO: remove this? unreachable
        await cl.ErrorMessage(content="No active connection. Please refresh.").send()
        return

    msg = cl.Message(content="")
    await msg.send()
    cl.user_session.set("active_msg", msg)

    # TODO: look into lack of formatting on messages displayed. Are we stripping too much in backend?
    await manager.send({"message": message.content})


@cl.on_chat_end
async def on_end():
    """Cleanup per-session websocket manager."""
    manager: WSManager = cl.user_session.get("ws_manager")
    if manager:
        await manager.stop()
    print("Chat ended and connection closed.")


@cl.on_stop
async def on_stop():
    print("Stop button pressed")
