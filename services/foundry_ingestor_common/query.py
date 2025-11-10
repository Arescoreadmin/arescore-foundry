"""Lightweight query helpers used by the ingestor tests.

This module intentionally implements a very small subset of the SQLAlchemy
query API so that the ingestor services can run without the external
``sqlalchemy`` dependency. Only what is required by the tests is provided
here: the :func:`select` helper and a result object exposing ``scalar``
accessors.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, Iterable, List, Sequence, Type, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class SelectQuery(Generic[T]):
    """Representation of a ``select`` request for a model class."""

    model: Type[T]

    # The real SQLAlchemy ``Select`` object exposes ``where`` and many other
    # methods. The ingestor tests only call ``select(Model)`` without further
    # filtering, so ``where`` simply raises a descriptive error to make misuse
    # obvious during development.
    def where(self, *_, **__):  # pragma: no cover - defensive programming
        raise NotImplementedError(
            "Filtering is not supported by the lightweight SelectQuery stub"
        )


def select(model: Type[T]) -> SelectQuery[T]:
    """Return a ``SelectQuery`` for the provided model class."""

    return SelectQuery(model)


class Result(Generic[T]):
    """Container for rows returned from :meth:`Session.execute`."""

    def __init__(self, items: Sequence[T]):
        self._items: List[T] = list(items)

    # The tests rely on ``scalar_one``/``scalar_one_or_none`` and ``scalars``.
    def scalar_one(self) -> T:
        if len(self._items) != 1:  # pragma: no cover - sanity guard
            raise ValueError("Expected exactly one result")
        return self._items[0]

    def scalar_one_or_none(self) -> T | None:
        if not self._items:
            return None
        if len(self._items) == 1:
            return self._items[0]
        raise ValueError("Expected zero or one result")  # pragma: no cover

    def scalars(self) -> Iterable[T]:
        return list(self._items)


__all__ = ["Result", "SelectQuery", "select"]
