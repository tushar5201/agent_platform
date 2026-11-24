import re

_CTRL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")
_JWT = re.compile(r"\beyJ[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]{5,}\b")
_BEARER = re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]+")
_KEYVAL = re.compile(
    r"(?i)\b(api[_-]?key|secret|token|password|passwd|authorization)\b(\s*[:=]\s*)[^\s,;\"']+"
)
_LONG_TOKEN = re.compile(r"\b[A-Za-z0-9_\-]{40,}\b")
_INJECTION = re.compile(
    r"(?i)(ignore\s+(all\s+|any\s+)?(previous|prior|above|earlier)\s+(instructions|rules|prompts?)"
    r"|disregard\s+.{0,40}(instructions|rules)"
    r"|you\s+are\s+now\b"
    r"|(reveal|print|show|output)\s+.{0,30}(system\s+prompt|api\s*key|secret|token))"
)
_ID = re.compile(r"^[A-Za-z0-9_.:-]{1,128}$")
_CONV = re.compile(r"^[A-Za-z0-9_-]{1,64}$")

def redact(text: str) -> str:
    text = _JWT.sub("[REDACTED_JWT]", text)
    text = _BEARER.sub("Bearer [REDACTED]", text)
    text = _KEYVAL.sub(lambda m: f"{m.group(1)}{m.group(2)}[REDACTED]", text)
    return _LONG_TOKEN.sub("[REDACTED_TOKEN]", text)

def truncate(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + f"\n...[truncated {len(text) - max_chars} chars]"

def looks_like_injection(text: str) -> bool:
    return bool(_INJECTION.search(text))

def wrap_untrusted(tool: str, text: str, max_chars: int) -> tuple[str, bool]:
    """Clear tool output and wrap it so the model treats it as data, not instructions."""
    clean = redact(_CTRL.sub("", text))
    clean = truncate(clean, max_chars)
    flagged = looks_like_injection(clean)
    clean = clean.replace("</tool_result", "<\\/tool_result")
    safe_tool = re.sub(r"[^A-Za-z0-9_.-]", "", tool)[:64]
    attrs = f'name = "{safe_tool}" trust="untrusted"' + (' suspicious="true"' if flagged else "")
    return f"<tool_result {attrs}>\n{clean}\n</tool_result>", flagged

def make_thread_id(user_id: str, conversation_id: str) -> str:
    """Namespace the thread by the VERIFIED user id so users can never reach each other's state."""
    if not _ID.match(user_id):
        raise ValueError("invalid user id")
    if not _CONV.match(conversation_id):
        raise ValueError("invalid conversation id")
    return f"{user_id}:{conversation_id}"

def text_of(content) -> str:
    """Flatten str or content-block lists to plain text."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for b in content:
            if isinstance(b, str):
                parts.append(b)
            elif isinstance(b, dict) and b.get("type") == "text":
                parts.append(str(b.get("text", "")))
        return "".join(parts)
    return str(content)

