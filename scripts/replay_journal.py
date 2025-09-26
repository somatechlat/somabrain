import json
from pathlib import Path

def replay(journal_dir, checkpoint_path, dry_run=True, batch=1):
    """
    Minimal replay implementation for test compatibility.
    Reads journal files and writes a checkpoint JSON with offsets.
    """
    journal_dir = Path(journal_dir)
    checkpoint_path = Path(checkpoint_path)
    offsets = {}
    if checkpoint_path.exists():
        try:
            offsets = json.loads(checkpoint_path.read_text())
        except Exception:
            offsets = {}
    for file in journal_dir.glob("*.jsonl"):
        lines = file.read_text().splitlines()
        prev_offset = offsets.get(file.name, {}).get("offset", 0)
        new_offset = min(prev_offset + batch, len(lines))
        offsets[file.name] = {"offset": new_offset}
    checkpoint_path.write_text(json.dumps(offsets, indent=2))
    return offsets
