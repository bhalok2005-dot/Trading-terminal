from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from ..models import SyncLog
from .connectors import TradeConnector
from .importer import upsert_trades


def sync_trades(session: Session, account_id: int, connector: TradeConnector) -> SyncLog:
    sync_log = SyncLog(account_id=account_id, started_at=datetime.now(timezone.utc), status="running")
    session.add(sync_log)
    session.commit()
    session.refresh(sync_log)
    sync_log_id = sync_log.id

    try:
        rows = list(connector.fetch_trades())
        inserted, updated = upsert_trades(session, account_id, rows)
        sync_log = session.query(SyncLog).filter(SyncLog.id == sync_log_id).one()
        sync_log.trades_fetched = len(rows)
        sync_log.inserted = inserted
        sync_log.updated = updated
        sync_log.status = "success"
        sync_log.ended_at = datetime.now(timezone.utc)
        session.commit()
        session.refresh(sync_log)
        return sync_log
    except Exception as error:
        session.rollback()
        sync_log = session.query(SyncLog).filter(SyncLog.id == sync_log_id).one()
        sync_log.status = "failed"
        sync_log.errors = f"{type(error).__name__}: {error}"[:500]
        sync_log.ended_at = datetime.now(timezone.utc)
        session.commit()
        raise