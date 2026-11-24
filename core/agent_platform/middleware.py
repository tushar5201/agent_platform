"""Agent middleware: wraps every tool call with audit, redaction and untrusted-data framing."""
from __future__ import annotations

import time

from langchain.agents.middleware import AgentMiddleware
from langchain_core.messages import ToolMessage
from langgraph.errors import GraphBubbleUp

from .guardrails import redact, text_of, wrap_untrusted
from .store import Store


class GuardMiddleware(AgentMiddleware):
    def __init__(self, *, store: Store, user_id: str, thread_id: str, max_result_chars: int):
        super().__init__()
        self.store, self.user_id, self.thread_id = store, user_id, thread_id
        self.max_result_chars = max_result_chars

    async def awrap_tool_call(self, request, handler):
        call = request.tool_call
        name = call.get("name", "unknown")
        args = {k: redact(str(v))[:200] for k, v in (call.get("args") or {}).items()}
        start = time.perf_counter()
        ok, flagged = True, False
        try:
            result = await handler(request)
        except GraphBubbleUp:
            raise
        except Exception:
            ok = False
            result = ToolMessage(
                content="Tool call failed.", tool_call_id=call["id"], name=name, status="error"
            )
        if isinstance(result, ToolMessage):
            if result.status == "error":
                ok = False
            body, flagged = wrap_untrusted(name, text_of(result.content), self.max_result_chars)
            result = ToolMessage(
                content=body, tool_call_id=result.tool_call_id, name=result.name or name,
                status=result.status,
            )
        await self.store.audit(
            user_id=self.user_id, thread_id=self.thread_id, tool=name, args=args, ok=ok,
            flagged=flagged, ms=int((time.perf_counter() - start) * 1000),
        )
        return result
