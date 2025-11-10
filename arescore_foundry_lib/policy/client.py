"""Compatibility wrapper for legacy imports of :mod:`arescore_foundry_lib.policy`.

Historically the policy helpers lived in a ``client`` submodule that imported
``httpx`` as soon as it was imported.  Some lightweight containers – including
the orchestrator image used by the ``smoke_overlay`` GitHub workflow – do not
install ``httpx`` which resulted in an import-time ``ModuleNotFoundError``.  The
implementation was moved into :mod:`arescore_foundry_lib.policy` so that the
optional dependency could be resolved lazily.

This module simply re-exports the public API from the package to preserve the
older import path without re-introducing the eager dependency.
"""

from __future__ import annotations

from . import (
    OPAClient,
    PolicyBundle,
    PolicyError,
    PolicyLoadError,
    PolicyModule,
    PolicyPushError,
    build_policy_bundle,
    discover_policy_modules,
    load_policy_module,
)

__all__ = [
    "PolicyError",
    "PolicyLoadError",
    "PolicyPushError",
    "PolicyModule",
    "PolicyBundle",
    "load_policy_module",
    "discover_policy_modules",
    "build_policy_bundle",
    "OPAClient",
]
