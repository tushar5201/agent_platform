"""FastAPI app. Only a trusted gateway (or demo mode) may call /v1/chat."""
from __future__ import annotations

import hmac
import json
import re
from contextlib import asynccontextmanager
from pathlib import Path

import aiosqlite
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from pydantic import BaseModel

from .config import Settings, get_settings
from .service import Caller, ChatRejected, ChatService
from .store import Store

_SESSION = re.compile(r"^[A-Za-z0-9_-]{8,64}$")


class ChatRequest(BaseModel):
    message: str
    conversation_id: str | None = None


def resolve_caller(request: Request, s: Settings) -> Caller:
    h = request.headers
    key = h.get("x-internal-key")
    expected = s.internal_key.get_secret_value()
    if key is not None:
        if not expected or not hmac.compare_digest(key, expected):
            raise HTTPException(401, "Unauthorized")
        user_id = h.get("x-user-id", "")
        if not user_id:
            raise HTTPException(401, "Missing verified user id")
        return Caller(user_id=user_id, token=h.get("x-user-token", ""))
    if s.demo_mode:
        session = h.get("x-demo-session", "")
        if not _SESSION.match(session):
            raise HTTPException(401, "Missing demo session")
        return Caller(user_id=f"demo-{session}", token="demo-token")
    raise HTTPException(401, "Unauthorized")


def sse(ev: dict) -> str:
    return f"event: {ev['event']}\ndata: {json.dumps(ev['data'])}\n\n"


def create_app(settings: Settings | None = None, model=None, fallbacks=None) -> FastAPI:
    s = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        Path(s.data_dir).mkdir(parents=True, exist_ok=True)
        store = Store(str(Path(s.data_dir) / "agent.db"))
        await store.open()
        conn = await aiosqlite.connect(str(Path(s.data_dir) / "checkpoints.db"))
        saver = AsyncSqliteSaver(conn)
        await saver.setup()
        app.state.service = ChatService(s, store, saver, model=model, fallbacks=fallbacks)
        app.state.store = store
        yield
        await conn.close()
        await store.close()

    app = FastAPI(title="agent-platform", lifespan=lifespan)

    @app.get("/health")
    async def health():
        return {"status": "ok", "kill_switch": app.state.service.kill_switch_on()}

    @app.post("/v1/chat")
    async def chat(body: ChatRequest, request: Request):
        caller = resolve_caller(request, s)
        svc: ChatService = request.app.state.service
        try:
            thread_id = await svc.precheck(caller, body.message, body.conversation_id)
        except ChatRejected as e:
            raise HTTPException(e.status, e.detail) from e

        async def gen():
            async for ev in svc.stream(caller, body.message.strip(), thread_id):
                yield sse(ev)

        return StreamingResponse(gen(), media_type="text/event-stream",
                                 headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

    @app.get("/v1/chat/{conversation_id}/history")
    async def history(conversation_id: str, request: Request):
        caller = resolve_caller(request, s)
        try:
            return {"messages": await request.app.state.service.history(caller, conversation_id)}
        except ChatRejected as e:
            raise HTTPException(e.status, e.detail) from e

    if s.demo_mode and Path(s.ui_dir).is_dir():
        app.mount("/", StaticFiles(directory=s.ui_dir, html=True), name="ui")
    return app


def app_factory() -> FastAPI:
    load_dotenv()  # provider keys (GROQ_API_KEY, NVIDIA_API_KEY) must reach os.environ
    return create_app()
