from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Protocol

from ..config import settings
from .importer import parse_csv_rows


class TradeConnector(Protocol):
    def fetch_trades(self) -> list[Mapping[str, Any]]: ...


@dataclass
class BrokerConfig:
    broker: str = "MetaTrader 5"
    account: str | None = None
    login: str | None = None
    password: str | None = None
    server: str | None = None
    path: str | None = None
    data: list[Mapping[str, Any]] = field(default_factory=list)
    is_demo: bool = True

    @classmethod
    def from_json(cls, raw: str | Mapping[str, Any] | None) -> "BrokerConfig":
        if raw is None:
            return cls()

        if isinstance(raw, Mapping):
            payload = dict(raw)
        else:
            text = raw.strip()
            if not text:
                return cls()
            if text.startswith("{") or text.startswith("["):
                payload = json.loads(text)
            else:
                path = Path(text)
                if not path.exists():
                    raise ValueError("MT5_CONFIG must be valid JSON content or a path to a JSON file")
                payload = json.loads(path.read_text(encoding="utf-8"))

        if isinstance(payload, list):
            payload = {"data": payload}
        if not isinstance(payload, dict):
            raise ValueError("Broker configuration must resolve to a JSON object")

        data = payload.get("data") or payload.get("trades") or []
        return cls(
            broker=str(payload.get("broker") or payload.get("platform") or "MetaTrader 5"),
            account=payload.get("account"),
            login=payload.get("login"),
            password=payload.get("password"),
            server=payload.get("server"),
            path=payload.get("path"),
            data=list(data) if isinstance(data, list) else [],
            is_demo=bool(payload.get("is_demo", True)),
        )

    @classmethod
    def from_env(cls) -> "BrokerConfig":
        return cls.from_json(settings.MT5_CONFIG)


class MetaTrader5Connector:
    def __init__(self, config: BrokerConfig | Mapping[str, Any] | str | None = None) -> None:
        if isinstance(config, BrokerConfig):
            self.config = config
        elif config is None:
            self.config = BrokerConfig.from_env()
        else:
            self.config = BrokerConfig.from_json(config)

    def fetch_trades(self) -> list[Mapping[str, Any]]:
        if not self.config.data:
            raise ValueError(
                "MetaTrader 5 connector is not configured. Set MT5_CONFIG to JSON with a 'data' list or point it to a JSON file."
            )
        return list(self.config.data)


class CsvTradeConnector:
    def __init__(self, csv_text: str) -> None:
        self.csv_text = csv_text

    def fetch_trades(self) -> list[Mapping[str, Any]]:
        return parse_csv_rows(self.csv_text)
