import hashlib

from conftest import gw_headers, parse_sse, tool_call
from langchain_core.messages import AIMessage

CHAT = "/v1/chat"


def post(client, msg="hi", headers=None, conv="conv1"):
    return client.post(CHAT, json={"message": msg, "conversation_id": conv},
                       headers=headers if headers is not None else gw_headers())


def test_health_open_and_chat_needs_auth(make_client):
    c, _ = make_client([AIMessage(content="x")])
    assert c.get("/health").json()["status"] == "ok"
    assert post(c, headers={}).status_code == 401
    assert post(c, headers={"x-internal-key": "wrong", "x-user-id": "u1"}).status_code == 401
    assert post(c, headers={"x-internal-key": "test-key"}).status_code == 401  # no user id


def test_empty_internal_key_never_matches(make_client):
    c, _ = make_client([AIMessage(content="x")], internal_key="")
    assert post(c, headers={"x-internal-key": "", "x-user-id": "u1"}).status_code == 401


def test_plain_answer_streams_token_and_done_with_disclaimer(make_client):
    c, _ = make_client([AIMessage(content="Hello there")])
    r = post(c)
    assert r.status_code == 200
    ev = parse_sse(r.text)
    assert ("token", {"text": "Hello there"}) in ev
    kind, data = ev[-1]
    assert kind == "done" and data["conversation_id"] == "conv1"
    assert "not financial" in data["disclaimer"]


def test_tool_call_end_to_end_with_token_passthrough(make_client):
    token = "tok-abc-123"
    c, model = make_client([tool_call("demo_whoami"), AIMessage(content="Done")])
    r = post(c, headers=gw_headers(token=token))
    names = [e for e, _ in parse_sse(r.text)]
    assert names[:2] == ["tool_start", "tool_end"] and names[-1] == "done"
    shown = str(model.seen[1][-1].content)  # what the model saw after the tool ran
    assert 'trust="untrusted"' in shown
    assert hashlib.sha256(token.encode()).hexdigest()[:8] in shown  # MCP server got the user token
    assert token not in shown


def test_prompt_injection_in_tool_result_is_flagged_and_audited(make_client):
    c, model = make_client([tool_call("demo_read_note", {"note_id": 3}), AIMessage(content="ok")])
    post(c)
    shown = str(model.seen[1][-1].content)
    assert 'suspicious="true"' in shown
    rows = c.portal.call(c.app.state.store.recent_audit, "u1")
    assert rows[0]["tool"] == "demo_read_note" and rows[0]["flagged"] == 1 and rows[0]["ok"] == 1


def test_memory_persists_and_threads_are_isolated_per_user(make_client):
    c, model = make_client([AIMessage(content="first"), AIMessage(content="second"),
                            AIMessage(content="third")])
    post(c, "remember banana", conv="k1")
    post(c, "what did I say?", conv="k1")
    second_turn = [str(m.content) for m in model.seen[1]]
    assert any("remember banana" in t for t in second_turn)
    post(c, "hello", conv="k1", headers=gw_headers(user="u2"))  # same conv id, different user
    third_turn = [str(m.content) for m in model.seen[2]]
    assert not any("banana" in t for t in third_turn)


def test_kill_switch_blocks(make_client):
    c, _ = make_client([AIMessage(content="x")], kill_switch=True)
    assert post(c).status_code == 503


def test_daily_cap_returns_429(make_client):
    c, _ = make_client([AIMessage(content="x")], daily_chat_cap=2)
    assert [post(c).status_code for _ in range(3)] == [200, 200, 429]


def test_input_validation(make_client):
    c, _ = make_client([AIMessage(content="x")], max_input_chars=10)
    assert post(c, "a" * 11).status_code == 413
    assert post(c, "   ").status_code == 422
    assert post(c, "ok", conv="bad/conv").status_code == 422


def test_tool_call_limit_stops_runaway_loop(make_client):
    c, _ = make_client([tool_call("demo_get_time", id=f"c{i}") for i in range(30)],
                       max_tool_calls=2, max_model_calls=4)
    r = post(c)
    assert parse_sse(r.text)[-1][0] in {"done", "error"}  # terminates, no infinite loop


def test_dead_mcp_server_does_not_break_chat(make_client, tmp_path):
    c, _ = make_client([AIMessage(content="still works")])
    svc = c.app.state.service
    svc.servers = {"dead": {"url": "http://127.0.0.1:1/mcp", "transport": "streamable_http"}}
    ev = parse_sse(post(c).text)
    assert ("notice", {"unavailable_tool_servers": ["dead"]}) in ev
    assert ("token", {"text": "still works"}) in ev


def test_blank_groq_key_gives_503_not_a_stream(tmp_path, monkeypatch):
    from agent_platform.api import create_app
    from agent_platform.config import Settings
    from fastapi.testclient import TestClient

    monkeypatch.setenv("GROQ_API_KEY", "")
    s = Settings(internal_key="test-key", data_dir=str(tmp_path), mcp_servers_file="none.json")
    with TestClient(create_app(s)) as c:
        assert post(c).status_code == 503


def test_fallback_model_used_when_primary_fails(tmp_path, demo_url):
    from agent_platform.api import create_app
    from agent_platform.config import Settings
    from conftest import ScriptedModel
    from fastapi.testclient import TestClient
    from langchain_core.language_models.chat_models import BaseChatModel
    from langchain_core.messages import AIMessage

    class Failing(BaseChatModel):
        @property
        def _llm_type(self):
            return "failing"

        def bind_tools(self, tools, **kw):
            return self

        def _generate(self, *a, **kw):
            raise RuntimeError("429 rate limited")

    s = Settings(internal_key="test-key", data_dir=str(tmp_path), mcp_servers_file="none.json")
    backup = ScriptedModel(script=[AIMessage(content="from backup")], seen=[])
    with TestClient(create_app(s, model=Failing(), fallbacks=[backup])) as c:
        ev = parse_sse(post(c).text)
    assert ("token", {"text": "from backup"}) in ev


def test_history_returns_plain_turns_and_is_per_user(make_client):
    c, _ = make_client([tool_call("demo_get_time"), AIMessage(content="It is noon")])
    post(c, "time?", conv="h1")
    h = c.get("/v1/chat/h1/history", headers=gw_headers()).json()["messages"]
    assert h == [{"role": "user", "text": "time?"}, {"role": "assistant", "text": "It is noon"}]
    other = c.get("/v1/chat/h1/history", headers=gw_headers(user="u2")).json()["messages"]
    assert other == []
    assert c.get("/v1/chat/h1/history").status_code == 401
    assert c.get("/v1/chat/bad.id/history", headers=gw_headers()).status_code == 422
