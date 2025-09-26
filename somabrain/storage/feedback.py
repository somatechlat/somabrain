"""Feedback persistence helpers."""

from __future__ import annotations

import datetime as dt
from typing import Optional

from sqlalchemy import Column, DateTime, Float, String, Text
import json
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from somabrain.storage import db


class FeedbackEvent(db.Base):
    __tablename__ = "feedback_events"

    id = Column(String(64), primary_key=True)
    session_id = Column(String(128), index=True, nullable=False)
    query = Column(Text, nullable=False)
    prompt = Column(Text, nullable=False)
    response_text = Column(Text, nullable=False)
    utility = Column(Float, nullable=False)
    reward = Column(Float, nullable=True)
    metadata_json = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=dt.datetime.utcnow)


class FeedbackStore:
    def __init__(self, engine_url: Optional[str] = None) -> None:
        self._engine = db.get_engine(engine_url)
        db.Base.metadata.create_all(self._engine)
        self._session_factory = db.get_session_factory(engine_url)

    def record(
        self,
        event_id: str,
        session_id: str,
        query: str,
        prompt: str,
        response_text: str,
        utility: float,
        reward: Optional[float] = None,
        metadata: Optional[dict] = None,
    ) -> None:
        session: Session = self._session_factory()
        try:
            rec = FeedbackEvent(
                id=event_id,
                session_id=session_id,
                query=query,
                prompt=prompt,
                response_text=response_text,
                utility=utility,
                reward=reward,
                metadata_json=json.dumps(metadata or {}),
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
            return session.query(FeedbackEvent).filter_by(session_id=session_id).all()
        finally:
            session.close()
