"""Shared utilities for Arescore Foundry services.

This package hosts light-weight helper modules that can be imported by the
individual micro-services that live in this repository.  Historically a few of
the FastAPI apps expected a package named :mod:`arescore_foundry_lib` to be
available on the ``PYTHONPATH``.  When running the services directly from the
repository that package did not exist which resulted in ``ImportError``
failures during start-up.  The modules provided here deliberately avoid heavy
dependencies so that they can be reused from multiple services without pulling
in extra requirements.
"""

from __future__ import annotations

__all__ = ["policy"]

