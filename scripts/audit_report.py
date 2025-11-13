#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence


RELATIVE_SINCE = re.compile(r"^(?P<value>\d+)(?P<unit>[smhd])$")


def load_events(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        raise SystemExit(f"Audit file not found: {path}")

    events: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                # best-effort; don't blow up on a bad line
                continue
    return events


def parse_ts(ev: Dict[str, Any]) -> datetime | None:
    ts = ev.get("timestamp")
    if not isinstance(ts, str):
        return None
    try:
        cleaned = ts.strip()
        if cleaned.endswith("Z"):
            cleaned = cleaned[:-1] + "+00:00"
        parsed = datetime.fromisoformat(cleaned)
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except Exception:
        return None


def summarize(events: Sequence[Dict[str, Any]]) -> str:
    if not events:
        return "No events found."

    by_kind = Counter()
    by_template = Counter()
    by_tenant = Counter()
    scenario_ids: set[str] = set()

    for ev in events:
        kind = ev.get("event") or ev.get("kind") or "unknown"
        by_kind[kind] += 1

        payload = ev.get("payload") or {}
        if isinstance(payload, dict):
            tmpl = payload.get("template")
            sid = payload.get("scenario_id")
            tenant = payload.get("tenant_id")
            if isinstance(tmpl, str):
                by_template[tmpl] += 1
            if isinstance(sid, str):
                scenario_ids.add(sid)
            if isinstance(tenant, str):
                by_tenant[tenant] += 1

    timestamps = [ts for ts in (parse_ts(e) for e in events) if ts is not None]
    newest_ts = max(timestamps) if timestamps else None
    newest_ts_str = newest_ts.isoformat() if newest_ts else "unknown"

    lines: List[str] = []
    lines.append(f"Total events: {len(events)}")
    lines.append(f"Unique scenarios (by scenario_id): {len(scenario_ids)}")
    lines.append(f"Most recent event timestamp: {newest_ts_str}")
    lines.append("")
    lines.append("Events by kind:")
    for kind, count in by_kind.most_common():
        lines.append(f"  {kind}: {count}")

    if by_template:
        lines.append("")
        lines.append("scenario.created by template:")
        for tmpl, count in by_template.most_common():
            lines.append(f"  {tmpl}: {count}")

    if by_tenant:
        lines.append("")
        lines.append("Events by tenant:")
        for tenant, count in by_tenant.most_common():
            lines.append(f"  {tenant}: {count}")

    return "\n".join(lines)


def filter_events(
    events: Sequence[Dict[str, Any]],
    *,
    event_names: Iterable[str] | None = None,
    since: datetime | None = None,
) -> List[Dict[str, Any]]:
    allowed = {name for name in (event_names or []) if name}
    filtered: List[Dict[str, Any]] = []

    for ev in events:
        if allowed and (ev.get("event") or ev.get("kind")) not in allowed:
            continue

        if since is not None:
            ts = parse_ts(ev)
            if ts is None or ts < since:
                continue

        filtered.append(ev)

    return filtered


def parse_since(value: str | None) -> datetime | None:
    if value is None:
        return None

    candidate = value.strip()
    if not candidate:
        return None

    match = RELATIVE_SINCE.match(candidate.lower())
    if match:
        qty = int(match.group("value"))
        unit = match.group("unit")
        delta_map = {
            "s": timedelta(seconds=qty),
            "m": timedelta(minutes=qty),
            "h": timedelta(hours=qty),
            "d": timedelta(days=qty),
        }
        return datetime.now(timezone.utc) - delta_map[unit]

    cleaned = candidate
    if cleaned.endswith("Z"):
        cleaned = cleaned[:-1] + "+00:00"

    try:
        parsed = datetime.fromisoformat(cleaned)
    except Exception as exc:  # pragma: no cover - defensive branch
        raise SystemExit(
            "Unable to parse --since value. Use ISO8601 (e.g. 2024-05-01T12:00:00Z) "
            "or a relative duration like 12h."
        ) from exc

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _sort_by_timestamp(events: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    sentinel = datetime.min.replace(tzinfo=timezone.utc)
    return sorted(events, key=lambda ev: parse_ts(ev) or sentinel)


def format_event_text(ev: Dict[str, Any]) -> str:
    ts = ev.get("timestamp", "?")
    kind = ev.get("event") or ev.get("kind") or "unknown"
    payload = ev.get("payload") if isinstance(ev.get("payload"), dict) else {}
    extras: list[str] = []

    for label in ("scenario_id", "template", "tenant_id"):
        value = payload.get(label)
        if isinstance(value, str) and value:
            extras.append(f"{label}={value}")

    if payload:
        interesting = {k: v for k, v in payload.items() if k not in {"scenario_id", "template", "tenant_id"}}
        if interesting:
            extras.append(f"payload={json.dumps(interesting, ensure_ascii=False)}")

    suffix = f" {' '.join(extras)}" if extras else ""
    return f"{ts} {kind}{suffix}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize Foundry audit events.")
    parser.add_argument(
        "--path",
        "-p",
        default=None,
        help="Path to JSONL audit file (default: $FOUNDRY_TELEMETRY_PATH or audits/foundry-events.jsonl)",
    )
    parser.add_argument(
        "--event",
        "-e",
        action="append",
        dest="events",
        help="Filter by event name (can be supplied multiple times).",
    )
    parser.add_argument(
        "--since",
        help="Only include events newer than this ISO8601 timestamp or relative duration (e.g. 6h, 2d).",
    )
    parser.add_argument(
        "--show-events",
        action="store_true",
        help="Print the filtered events after the summary.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Limit for --show-events (0 = show all).",
    )
    parser.add_argument(
        "--output",
        choices=("text", "json"),
        default="text",
        help="Output format for --show-events (default: text).",
    )
    args = parser.parse_args()

    env_path = Path(
        (  # type: ignore[arg-type]
            __import__("os").environ.get("FOUNDRY_TELEMETRY_PATH", "audits/foundry-events.jsonl")
        )
    )
    path = Path(args.path) if args.path else env_path

    events = load_events(path)
    since = parse_since(args.since)
    filtered = filter_events(events, event_names=args.events, since=since)

    if args.events or since:
        filters: list[str] = []
        if args.events:
            filters.append("event in [" + ", ".join(args.events) + "]")
        if since:
            filters.append(f"since {since.isoformat()}")
        print("Filters: " + ", ".join(filters))
        print("")

    print(summarize(filtered))

    if args.show_events and filtered:
        print("")
        print("Events:")
        ordered = _sort_by_timestamp(filtered)
        if args.limit > 0:
            ordered = ordered[-args.limit :]

        for ev in ordered:
            if args.output == "json":
                print(json.dumps(ev, ensure_ascii=False))
            else:
                print(format_event_text(ev))


if __name__ == "__main__":
    main()
