# Site customization to ensure test environment bypasses strict real mode.
# This file is automatically imported by Python if present on the import path.
# It sets an environment variable that the test suite's conftest checks to
# decide whether to enforce strict real mode. By default we disable strict
# real mode for the test run, allowing fakeredis and other test fakes.
import os
os.environ.setdefault("SOMABRAIN_STRICT_REAL_BYPASS", "1")
