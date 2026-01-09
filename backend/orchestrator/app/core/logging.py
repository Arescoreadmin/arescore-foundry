"""Logging helpers for the orchestrator service."""

from __future__ import annotations

import logging

from .correlation import current_corr_id


class CorrIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.corr_id = ""
        try:
            record.corr_id = current_corr_id()
        except Exception:  # pragma: no cover - defensive
            pass
        return True


root = logging.getLogger()
root.handlers[:] = [logging.StreamHandler()]
root.handlers[0].addFilter(CorrIdFilter())
root.handlers[0].setFormatter(
    logging.Formatter(
        "%(asctime)s %(levelname)s corr_id=%(corr_id)s %(name)s: %(message)s"
    )
)
root.setLevel(logging.INFO)
