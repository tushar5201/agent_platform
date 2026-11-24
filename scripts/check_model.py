import sys
import time

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_core.tools import tool


@tool
def get_time(tz: str) -> str:
    """Current time in an IANA timezone."""
    return "2026-01-01T00:00:00"

def check(spec: str, runs: int = 3) -> None:
    model = init_chat_model(spec, temperature=0).bind_tools([get_time])
    ok, times = 0, []
    for _ in range(runs):
        t = time.perf_counter()
        try:
            msg = model.invoke("What time is it in Asia/Kolkata? Use the tool.")
            called = any(c["name"] == "get_time" for c in msg.tool_calls)
        except Exception as e:
            print(f"error: {type(e).__name__}")
            called = False
        times.append(time.perf_counter() - t)
        ok += called
    print(f"{spec}: tool call correct {ok}/{runs}, avg {sum(times) / runs:.2f}s")

if __name__ == "__main__":
    load_dotenv()
    for spec in sys.argv[1:] or ["groq:llama-3.3-70b-versatile"]:
        check(spec)
