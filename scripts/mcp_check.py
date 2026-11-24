import asyncio
import sys

from fastmcp import Client
from fastmcp.client import StreamableHttpTransport


async def main(url: str) -> None:
    transport = StreamableHttpTransport(url, headers={"Authorization": "Bearer demo-token"})
    try:
        client = Client(transport=transport)
        await client.__aenter__()
    except Exception:
        sys.exit(f"Can't reach {url}. Is the MCP server running? (python packs/demo/server.py)")
    async with client as c:
        tools = await c.list_tools()
        print("tools:",", ".join(t.name for t in tools))
        for name, args in [("calculate", {"expression": "2+3*4"}), ("whoami", {})]:
            if any(t.name == name for t in tools):
                res = await c.call_tool(name, args)
                print(f"{name} -> ", res.data)


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8001/mcp"))