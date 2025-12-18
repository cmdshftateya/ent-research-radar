import os


def _as_bool(value: str) -> bool:
    return value.lower() in {"1", "true", "yes", "on"}


OFFLINE = _as_bool(os.getenv("ENT_OFFLINE", "false"))
HTTP_TIMEOUT = float(os.getenv("ENT_HTTP_TIMEOUT", "15"))
USER_AGENT = os.getenv(
    "ENT_USER_AGENT",
    "ent-research-tool/0.1 (+https://example.local; contact=ent-tool@example.local)",
)
