"""Storage persistence for Dynamic Task Registry."""

from __future__ import annotations

import uuid
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from somabrain.storage import db
from somabrain.db.models.task import TaskRegistry
from somabrain.api.schemas.task import TaskCreate, TaskUpdate

class TaskRegistryStore:
    def __init__(self, engine_url: Optional[str] = None) -> None:
        self._engine = db.get_engine(engine_url)
        # We generally expect migrations to handle table creation,
        # but create_all is safe if tables exist.
        db.Base.metadata.create_all(self._engine)
        self._session_factory = db.get_session_factory(engine_url)

    def create(self, task_data: TaskCreate) -> TaskRegistry:
        session: Session = self._session_factory()
        try:
            task = TaskRegistry(
                id=uuid.uuid4().hex,
                name=task_data.name,
                description=task_data.description,
                schema=task_data.schema,
                version=task_data.version,
                rate_limit_per_min=task_data.rate_limit_per_min,
                policy_tags=task_data.policy_tags,
            )
            session.add(task)
            session.commit()
            session.refresh(task)
            return task
        except SQLAlchemyError:
            session.rollback()
            raise
        finally:
            session.close()

    def get_by_name(self, name: str) -> Optional[TaskRegistry]:
        session: Session = self._session_factory()
        try:
            return session.query(TaskRegistry).filter_by(name=name).first()
        finally:
            session.close()

    def get(self, task_id: str) -> Optional[TaskRegistry]:
        session: Session = self._session_factory()
        try:
            return session.query(TaskRegistry).filter_by(id=task_id).first()
        finally:
            session.close()

    def list(self, limit: int = 100, offset: int = 0) -> Tuple[List[TaskRegistry], int]:
        session: Session = self._session_factory()
        try:
            query = session.query(TaskRegistry)
            total = query.count()
            tasks = query.order_by(TaskRegistry.created_at.desc()).offset(offset).limit(limit).all()
            return tasks, total
        finally:
            session.close()

    def update(self, task_id: str, updates: TaskUpdate) -> Optional[TaskRegistry]:
        session: Session = self._session_factory()
        try:
            task = session.query(TaskRegistry).filter_by(id=task_id).first()
            if not task:
                return None

            update_data = updates.model_dump(exclude_unset=True)
            for key, value in update_data.items():
                setattr(task, key, value)

            session.commit()
            session.refresh(task)
            return task
        except SQLAlchemyError:
            session.rollback()
            raise
        finally:
            session.close()

    def delete(self, task_id: str) -> bool:
        session: Session = self._session_factory()
        try:
            task = session.query(TaskRegistry).filter_by(id=task_id).first()
            if not task:
                return False
            session.delete(task)
            session.commit()
            return True
        except SQLAlchemyError:
            session.rollback()
            raise
        finally:
            session.close()
