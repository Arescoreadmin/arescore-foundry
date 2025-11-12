import logging
import json
import sys
import uuid
from contextvars import ContextVar

# Context variable for correlation IDs
_request_id_ctx = ContextVar("request_id", default=None)

def get_request_id() -> str:
    rid = _request_id_ctx.get()
    if rid is None:
        rid = str(uuid.uuid4())
        _request_id_ctx.set(rid)
    return rid

class JsonFormatter(logging.Formatter):
    def format(self, record):
        base = {
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "time": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "request_id": get_request_id(),
        }
        return json.dumps(base, separators=(",", ":"))

def configure_logging():
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(logging.INFO)
