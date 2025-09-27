"""Simple DB benchmark using SQLAlchemy session factory from the project.

Usage:
  python benchmarks/db_bench.py --iterations 1000

This will open sessions and perform simple insert/select cycles against the configured DB.
"""
import argparse
import time

from somabrain.storage.db import get_session_factory, Base, get_engine
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import Session

# Minimal test table model declared here to avoid touching application models
class _BenchItem(Base):
    __tablename__ = "bench_item"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(256), nullable=False)


def setup_db(url: str | None = None):
    engine = get_engine(url)
    Base.metadata.create_all(engine)
    return get_session_factory(url)


def run(iterations: int, url: str | None = None):
    SessionFactory = setup_db(url)
    t0 = time.perf_counter()
    with Session(SessionFactory()) as s:
        for i in range(iterations):
            item = _BenchItem(name=f"bench-{i}")
            s.add(item)
            if i % 100 == 0:
                s.flush()
        s.commit()
    t1 = time.perf_counter()
    print(f"Inserted {iterations} rows in {t1-t0:.3f}s ({iterations/(t1-t0):.1f} ops/s)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--iterations", type=int, default=1000)
    parser.add_argument("--db", default=None)
    args = parser.parse_args()
    run(args.iterations, args.db)
