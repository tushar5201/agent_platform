"""Chat with the agent in the terminal, no API or UI needed. Fastest feedback loop.

Usage: python scripts/chat_cli.py      (needs the MCP server running and a key in .env)
Type 'exit' to quit.
"""
import asyncio
from pathlib import Path

import aiosqlite
from agent_platform.config import Settings
from agent_platform.service import Caller, ChatRejected, ChatService
from agent_platform.store import Store
from dotenv import load_dotenv
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver


async def main(model=None, lines=None) -> None:
    load_dotenv()
    s = Settings()
    Path(s.data_dir).mkdir(parents=True, exist_ok=True)
    store = Store(str(Path(s.data_dir) / "cli.db"))
    await store.open()
    async with aiosqlite.connect(Path(s.data_dir) / "cli-checkpoints.db") as conn:
        saver = AsyncSqliteSaver(conn)
        await saver.setup()
        svc = ChatService(s, store, saver, model=model)
        caller = Caller("cli-user", "cli-token")
        feed = iter(lines) if lines is not None else None
        while True:
            text = next(feed, "exit") if feed is not None else input("you> ")
            if text.strip().lower() in {"exit", "quit"}:
                break
            try:
                thread = await svc.precheck(caller, text, "cli")
            except ChatRejected as e:
                print(f"[rejected {e.status}] {e.detail}")
                continue
            async for ev in svc.stream(caller, text, thread):
                d = ev["data"]
                if ev["event"] == "token":
                    print(d["text"], end="", flush=True)
                elif ev["event"] == "tool_start":
                    print(f"\n[tool] {d['name']} {d['args']}")
                elif ev["event"] == "tool_end":
                    print(f"[tool] {d['name']} {'ok' if d['ok'] else 'FAILED'}")
                elif ev["event"] == "error":
                    print(f"\n[error] {d['message']}")
                elif ev["event"] == "notice":
                    print(f"\n[MCP NOTICE] {d}")
            print()
    await store.close()


if __name__ == "__main__":
    asyncio.run(main())
