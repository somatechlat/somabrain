import os
import tempfile

import pytest

from somabrain.constitution.storage import ConstitutionStorage
from somabrain.storage import db


@pytest.fixture()
def sqlite_env(tmp_path):
    db_path = tmp_path / "constitution.db"
    url = f"sqlite:///{db_path}"
    db.reset_engine(url)
    yield url
    db.reset_engine()


def test_storage_roundtrip(sqlite_env):
    storage = ConstitutionStorage(db_url=sqlite_env)
    constitution = {"version": "1", "rules": {}, "utility_params": {"lambda": 1}}
    checksum = storage.save_new(constitution)
    record = storage.load_active()
    assert record.checksum == checksum
    assert record.document == constitution
    # record signature
    storage.record_signature(checksum, "signer-a", "deadbeef")
    sigs = storage.get_signatures(checksum)
    assert any(s["signer_id"] == "signer-a" for s in sigs)


def test_snapshot_local(tmp_path, sqlite_env):
    storage = ConstitutionStorage(db_url=sqlite_env)
    constitution = {"version": "2"}
    checksum = storage.save_new(constitution)
    os.environ["SOMABRAIN_CONSTITUTION_SNAPSHOT_DIR"] = str(tmp_path)
    try:
        path = storage.snapshot(constitution, checksum, metadata={"note": "test"})
        assert path is not None
        assert os.path.exists(path)
    finally:
        os.environ.pop("SOMABRAIN_CONSTITUTION_SNAPSHOT_DIR")
