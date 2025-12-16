"""Token ledger persistence for SomaBrain."""

from __future__ import annotations

import datetime as dt
from typing import Optional

from sqlalchemy import Column, DateTime, Float, String
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from somabrain.storage import db


class TokenUsage(db.Base):
    __tablename__ = "token_usage"

    id = Column(String(64), primary_key=True)
    session_id = Column(String(128), index=True, nullable=False)
    tenant_id = Column(String(128), nullable=True)
    tokens = Column(Float, nullable=False)
    model = Column(String(128), nullable=True)
    created_at = Column(
        DateTime(timezone=True), nullable=False, default=dt.datetime.utcnow
    )


class TokenLedger:
    def __init__(self, engine_url: Optional[str] = None) -> None:
        self._engine = db.get_engine(engine_url)
        db.Base.metadata.create_all(self._engine)
        self._session_factory = db.get_session_factory(engine_url)

    def record(
        self,
        entry_id: str,
        session_id: str,
        tokens: float,
        tenant_id: Optional[str] = None,
        model: Optional[str] = None,
    ) -> None:
        session: Session = self._session_factory()
        try:
            rec = TokenUsage(
                id=entry_id,
                session_id=session_id,
                tokens=tokens,
                tenant_id=tenant_id,
                model=model,
            )
            session.merge(rec)
            session.commit()
        except SQLAlchemyError:
            session.rollback()
            raise
        finally:
            session.close()

    def list_for_session(self, session_id: str):
        session: Session = self._session_factory()
        try:
            return session.query(TokenUsage).filter_by(session_id=session_id).all()
        finally:
            session.close()
