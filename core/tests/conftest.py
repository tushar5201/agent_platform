
import importlib.util
import json
import socket
import threading
import time
from pathlib import Path
from typing import Any

import pytest
import uvicorn
from agent_platform.api import create_app
from agent_platform.config import Settings
from fastapi.testclient import TestClient
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult

ROOT = Path(__file__).resolve().parents[2]


class ScriptedModel(BaseChatModel):
    """Returns scripted AIMessages in order and records what it was shown."""
    script: list[Any]
    i: int = 0
    seen: list[Any] = []

    @property
    def _llm_type(self) -> str:
        return "scripted"

    def bind_tools(self, tools, **kwargs):
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        self.seen.append(list(messages))
        msg = self.script[min(self.i, len(self.script) - 1)]
        self.i += 1
        return ChatResult(generations=[ChatGeneration(message=msg)])


def tool_call(name, args=None, id="c1"):
    return AIMessage(content="", tool_calls=[{"name": name, "args": args or {}, "id": id}])


@pytest.fixture(scope="session")
def demo_url():
    spec = importlib.util.spec_from_file_location("demo_server", ROOT / "packs/demo/server.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    with socket.socket() as sk:
        sk.bind(("127.0.0.1", 0))
        port = sk.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(mod.mcp.http_app(), port=port, log_level="warning"))
    t = threading.Thread(target=server.run, daemon=True)
    t.start()
    for _ in range(100):
        if server.started:
            break
        time.sleep(0.05)
    yield f"http://127.0.0.1:{port}/mcp"
    server.should_exit = True


@pytest.fixture
def make_client(tmp_path, demo_url):
    servers = tmp_path / "servers.json"
    servers.write_text(json.dumps({"servers": {"demo": {
        "url": demo_url, "transport": "streamable_http",
        "headers": {"Authorization": "Bearer {user_token}"}}}}))
    clients = []

    def _make(script, **overrides):
        opts = {"internal_key": "test-key", "mcp_servers_file": str(servers),
                "data_dir": str(tmp_path / "d"), "ui_dir": str(tmp_path / "noui")}
        settings = Settings(**{**opts, **overrides})
        model = ScriptedModel(script=script, seen=[])
        c = TestClient(create_app(settings, model=model))
        c.__enter__()
        clients.append(c)
        return c, model

    yield _make
    for c in clients:
        c.__exit__(None, None, None)


def parse_sse(text: str):
    events = []
    for block in text.strip().split("\n\n"):
        lines = block.split("\n")
        events.append((lines[0].removeprefix("event: "),
                       json.loads(lines[1].removeprefix("data: "))))
    return events


def gw_headers(user="u1", token="tok-abc-123"):
    return {"x-internal-key": "test-key", "x-user-id": user, "x-user-token": token}

