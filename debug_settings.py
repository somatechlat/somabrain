
import sys
import os

print(f"CWD: {os.getcwd()}")
print(f"Path: {sys.path}")

try:
    print("Attempting to import somabrain.app...")
    from somabrain import app
    print("Import successful!")
except Exception as e:
    print(f"Import failed: {e}")
    import traceback
    traceback.print_exc()

# Inspect settings again to see what it is NOW
try:
    from common.config.settings import settings
    print(f"Settings Class: {type(settings).__name__}")
    print(f"Has circuit_failure_threshold: {hasattr(settings, 'circuit_failure_threshold')}")
except Exception as e:
    print(f"Could not inspect settings: {e}")
