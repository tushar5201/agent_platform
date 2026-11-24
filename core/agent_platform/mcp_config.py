"""Load MCP server list from a config file and render per-user headers."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ALLOWED_TRANSPORTS = {"http", "streamable_http"}

def load_servers(path: str) -> dict[str, dict[str, Any]]:
    p = Path(path)
    if not p.exists():
        return {}
    servers = json.loads(p.read_text(encoding="utf-8")).get("servers", {})
    for name, cfg in servers.items():
        if "url" not in cfg:
            raise ValueError(f"MCP server '{name}' has no url")
        if cfg.get("transport", "streamable_http") not in ALLOWED_TRANSPORTS:
            raise ValueError(f"MCP server '{name}': only http transports are allowed")
    return servers

def connections_for(servers: dict[str, dict[str, Any]], user_token: str) -> dict[str, dict]:
    """Fresh connection dicts with the user's token injected into header templates.

    Headers are fixed per MCP connection, so call this once per chat request.
    The result holds the token. Never log it.
    """
    out: dict[str, dict] = {}
    for name, cfg in servers.items():
        headers = {
            k: v.replace("{user_token}", user_token) for k, v in cfg.get("headers", {}).items()
        }
        out[name] = {
            "url": cfg["url"],
            "transport": cfg.get("transport", "streamable_http"),
            "headers": headers,
        }
    return out
