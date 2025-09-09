#!/usr/bin/env bash
set -euo pipefail

# cleanup_repo.sh
# Safe repo cleanup for initial commit / GitHub upload.
# Usage: ./scripts/cleanup_repo.sh --dry-run  # show actions
#        ./scripts/cleanup_repo.sh --yes      # perform cleanup

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

DRY_RUN=1
if [ "${1:-}" = "--yes" ]; then
  DRY_RUN=0
fi

echo "Repo cleanup — root: $ROOT"

# Candidate garbage (found by scan)
declare -a CANDIDATES=(
  "pytest_output.txt"
  "somabrain.log"
  "audit_log.jsonl"
  "server.pid"
  "somabrain_uvicorn.pid"
  "somabrain_uvicorn_tail.pid"
  "docs/build"
  "docs/_build"
  "benchmarks/*.png"
  "benchmarks/*.csv"
  "__pycache__"
  "*.pyc"
  ".venv"
  "venv"
)

echo "The script will inspect and (optionally) archive/remove the following candidates:" 
for p in "${CANDIDATES[@]}"; do echo "  - $p"; done

ARCHIVE_DIR="$ROOT/artifacts/cleanup_$(date +%Y%m%d_%H%M%S)"
echo "Archive location: $ARCHIVE_DIR"

if [ $DRY_RUN -eq 1 ]; then
  echo "DRY RUN: no files will be deleted. Re-run with --yes to perform cleanup."
fi

mkdir -p "$ARCHIVE_DIR"

echo "Scanning and archiving candidate patterns"
for pat in "${CANDIDATES[@]}"; do
  # Use find to locate matches for patterns and names
  # If pattern contains a wildcard star, use -name; otherwise check literal path
  if echo "$pat" | grep -q '\*'; then
    # wildcard: convert to simple -name pattern (strip directories)
    dirpart="$(dirname "$pat")"
    namepart="$(basename "$pat")"
    if [ "$dirpart" = "." ] || [ "$dirpart" = "$pat" ]; then
      dirpart="$ROOT"
    else
      dirpart="$ROOT/$dirpart"
    fi
    if [ -d "$dirpart" ]; then
      while IFS= read -r -d $'\0' m; do
        echo "FOUND: $m"
        if [ $DRY_RUN -eq 1 ]; then
          echo "  (dry) would archive"
        else
          mkdir -p "$ARCHIVE_DIR/$(dirname "$m")"
          mv "$m" "$ARCHIVE_DIR/$(dirname "$m")/" || rm -rf "$m" || true
        fi
      done < <(find "$dirpart" -maxdepth 3 -name "$namepart" -print0)
    fi
  else
    # literal path
    if [ -e "$pat" ]; then
      echo "FOUND: $pat"
      if [ $DRY_RUN -eq 1 ]; then
        echo "  (dry) would archive"
      else
        mkdir -p "$ARCHIVE_DIR/$(dirname "$pat")"
        mv "$pat" "$ARCHIVE_DIR/$(dirname "$pat")/" || rm -rf "$pat" || true
      fi
    fi
  fi
done

echo "Now scanning for __pycache__ and .pyc files (portable find)"
if find . -type d -name '__pycache__' -print0 | read -r -d $'\0' then_found 2>/dev/null; then
  :
fi
# process pycache directories
while IFS= read -r -d $'\0' p; do
  echo "FOUND: $p"
  if [ $DRY_RUN -eq 1 ]; then
    echo "  (dry) would archive"
  else
    mkdir -p "$ARCHIVE_DIR/$(dirname "$p")"
    mv "$p" "$ARCHIVE_DIR/$(dirname "$p")/" || rm -rf "$p" || true
  fi
done < <(find . -type d -name '__pycache__' -print0)

# process .pyc files
while IFS= read -r -d $'\0' p; do
  echo "FOUND: $p"
  if [ $DRY_RUN -eq 1 ]; then
    echo "  (dry) would archive"
  else
    mkdir -p "$ARCHIVE_DIR/$(dirname "$p")"
    mv "$p" "$ARCHIVE_DIR/$(dirname "$p")/" || rm -f "$p" || true
  fi
done < <(find . -type f -name '*.pyc' -print0)

echo "Cleanup script complete."
if [ $DRY_RUN -eq 1 ]; then
  echo "To perform the actions shown, re-run: ./scripts/cleanup_repo.sh --yes"
else
  echo "Archived items moved to: $ARCHIVE_DIR"
fi

echo "Recommended next steps (run manually):"
echo "  ls -la artifacts/cleanup_*"
echo "  # If you want to initialize a fresh git repo:"
echo "  # git init"
echo "  # git add ."
echo "  # git commit -m 'Initial commit: cleaned repository'"
echo "  # git remote add origin <your-remote-url>"
echo "  # git branch -M main"
echo "  # git push -u origin main"
