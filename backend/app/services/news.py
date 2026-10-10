from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

from ..config import settings


def _as_utc(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
    text = str(value).strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    return parsed.astimezone(timezone.utc) if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


@dataclass(frozen=True)
class NewsEvent:
    symbol: str | None
    time: datetime
    impact: str = "medium"
    title: str = ""

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "NewsEvent":
        event_time = _as_utc(payload.get("time") or payload.get("event_time") or payload.get("date"))
        if event_time is None:
            raise ValueError("News event is missing a valid time")
        symbol = str(payload.get("symbol") or payload.get("pair") or payload.get("currency") or "").upper() or None
        impact = str(payload.get("impact") or payload.get("severity") or payload.get("level") or "medium").lower()
        title = str(payload.get("title") or payload.get("name") or "News event")
        return cls(symbol=symbol, time=event_time, impact=impact, title=title)

    @property
    def is_high_impact(self) -> bool:
        return self.impact in {"high", "critical", "important", "major", "1", "2"}


class NewsCalendar:
    def __init__(self, events: Iterable[Mapping[str, Any] | NewsEvent] | None = None) -> None:
        self.events = [
            event if isinstance(event, NewsEvent) else NewsEvent.from_mapping(event)
            for event in (events or [])
        ]

    @classmethod
    def from_config(cls, config: Any) -> "NewsCalendar":
        if config in (None, "", [], {}):
            return cls([])

        if isinstance(config, cls):
            return config

        if isinstance(config, str):
            text = config.strip()
            if not text:
                return cls([])
            try:
                parsed = json.loads(text)
            except json.JSONDecodeError:
                path = Path(text)
                if not path.exists():
                    return cls([])
                parsed = json.loads(path.read_text(encoding="utf-8"))
            return cls.from_config(parsed)

        if isinstance(config, Mapping):
            events = config.get("events") or config.get("news") or config.get("data") or []
            return cls(events)

        if isinstance(config, list):
            return cls(config)

        return cls([])

    @classmethod
    def from_env(cls) -> "NewsCalendar":
        return cls.from_config(getattr(settings, "NEWS_CONFIG", ""))

    def has_trade_overlap(self, symbol: str | None, entry_time: datetime | None, exit_time: datetime | None, window_minutes: int = 60) -> bool:
        if not self.events:
            return False

        trade_start = min([dt for dt in [entry_time, exit_time] if dt is not None], default=None)
        trade_end = max([dt for dt in [entry_time, exit_time] if dt is not None], default=None)
        if trade_start is None or trade_end is None:
            if entry_time is None and exit_time is None:
                return False
            anchor = entry_time or exit_time
            if anchor is None:
                return False
            trade_start = anchor - timedelta(minutes=window_minutes)
            trade_end = anchor + timedelta(minutes=window_minutes)

        for event in self.events:
            if not event.is_high_impact:
                continue
            if symbol and event.symbol and event.symbol.upper() != symbol.upper():
                continue
            event_start = event.time - timedelta(minutes=window_minutes)
            event_end = event.time + timedelta(minutes=window_minutes)
            if trade_start <= event_end and trade_end >= event_start:
                return True
        return False
