from __future__ import annotations

import csv
import io
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping

from sqlalchemy.orm import Session

from ..models import Trade


def _parse_float(value: Any, default: float = 0.0) -> float:
    if value is None or value == "":
        return default
    if isinstance(value, str):
        cleaned = value.strip().replace(",", "")
        if cleaned.upper() in {"N/A", "NA", "NONE", "NULL"}:
            return default
        try:
            return float(cleaned)
        except ValueError:
            return default
    return float(value)


def _parse_datetime(value: Any) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc) if value.tzinfo else value.replace(tzinfo=timezone.utc)
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


def normalize_trade_row(row: Mapping[str, Any], account_id: int) -> dict[str, Any]:
    side_value = str(row.get("side") or row.get("direction") or "long").strip().lower()
    if side_value in {"buy", "long", "b", "bullish"}:
        side = "long"
    elif side_value in {"sell", "short", "s", "bearish"}:
        side = "short"
    else:
        side = "long"

    entry_price = _parse_float(row.get("entry_price"), 0.0)
    exit_price = _parse_float(row.get("exit_price"), 0.0)
    stop_loss = row.get("stop_loss")
    take_profit = row.get("take_profit")
    volume = _parse_float(row.get("volume"), 0.0)
    net_profit = _parse_float(row.get("net_profit"), _parse_float(row.get("profit"), 0.0))

    risk_amount = _parse_float(row.get("risk_amount"), 0.0)
    if not risk_amount and entry_price and stop_loss is not None:
        stop_price = _parse_float(stop_loss, 0.0)
        risk_amount = abs(entry_price - stop_price) * volume * 100000.0
    if risk_amount == 0:
        risk_amount = None
    elif risk_amount is not None:
        risk_amount = round(risk_amount, 2)

    r_multiple = None
    if risk_amount not in (None, 0.0):
        r_multiple = net_profit / risk_amount

    normalized = {
        "account_id": account_id,
        "external_trade_id": str(row.get("external_trade_id") or row.get("trade_id") or row.get("id") or f"{account_id}-{row.get('symbol', 'trade')}-{row.get('entry_time') or 'unknown'}"),
        "symbol": str(row.get("symbol") or row.get("pair") or "UNKNOWN").upper(),
        "side": side,
        "volume": volume,
        "entry_price": entry_price,
        "exit_price": exit_price,
        "stop_loss": _parse_float(stop_loss, 0.0) if stop_loss not in (None, "") else None,
        "take_profit": _parse_float(take_profit, 0.0) if take_profit not in (None, "") else None,
        "entry_time": _parse_datetime(row.get("entry_time")),
        "exit_time": _parse_datetime(row.get("exit_time")),
        "profit": _parse_float(row.get("profit"), 0.0),
        "commission": _parse_float(row.get("commission"), 0.0),
        "swap": _parse_float(row.get("swap"), 0.0),
        "net_profit": net_profit,
        "risk_amount": risk_amount,
        "r_multiple": r_multiple,
        "strategy_id": str(row.get("strategy_id") or row.get("strategy") or "Manual"),
        "session": str(row.get("session") or row.get("market_session") or "London"),
    }
    return normalized


def upsert_trades(session: Session, account_id: int, rows: Iterable[Mapping[str, Any]]) -> tuple[int, int]:
    inserted = 0
    updated = 0

    for raw_row in rows:
        normalized = normalize_trade_row(raw_row, account_id)
        external_trade_id = normalized["external_trade_id"]

        existing = (
            session.query(Trade)
            .filter(Trade.account_id == account_id, Trade.external_trade_id == external_trade_id)
            .first()
        )

        if existing:
            for column_name, value in normalized.items():
                if column_name == "account_id":
                    continue
                if getattr(existing, column_name) != value:
                    setattr(existing, column_name, value)
            updated += 1
        else:
            session.add(Trade(**normalized))
            inserted += 1

    session.commit()
    return inserted, updated


def parse_csv_rows(csv_text: str) -> list[dict[str, Any]]:
    reader = csv.DictReader(io.StringIO(csv_text))
    return [dict(row) for row in reader]
