
"""Stub driver implementation."""
from .base import OverlayDriver


def get_driver() -> OverlayDriver:
    return OverlayDriver(name='l2tpv3')
