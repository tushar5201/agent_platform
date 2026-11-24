import importlib.util

import pytest
from conftest import ROOT
from fastmcp import Client


@pytest.fixture(scope="module")
def mod():
    spec = importlib.util.spec_from_file_location("demo_server", ROOT / "packs/demo/server.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


async def test_tools_listed_all_read_only(mod):
    async with Client(mod.mcp) as c:
        tools = await c.list_tools()
    assert {t.name for t in tools} == {"get_time", "calculate", "list_notes", "read_note", "whoami"}
    assert all(t.annotations and t.annotations.readOnlyHint for t in tools)


@pytest.mark.parametrize("expr,expected", [("2+3*4", "14"), ("-(2**3)", "-8")])
def test_calculate_ok(mod, expr, expected):
    assert mod.calculate(expr) == expected


@pytest.mark.parametrize("expr", ["__import__('os').system('x')", "2**9999", "a+1", "1;2"])
def test_calculate_rejects_unsafe(mod, expr):
    assert mod.calculate(expr).startswith("Cannot evaluate")
