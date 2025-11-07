import uuid
from contextvars import ContextVar

_corr: ContextVar[str] = ContextVar("corr_id", default="")

def set_corr_id(val: str | None) -> None:
    _corr.set(val or "")

def current_corr_id() -> str:
    return _corr.get() or "local-" + str(uuid.uuid4())
