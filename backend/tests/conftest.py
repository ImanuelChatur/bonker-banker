import os
import sys
from pathlib import Path

# backend/ is the app root (app.py imports `routes`, `engine`, ... as top-level packages)
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# The suite exercises pages directly, so login is off by default here; tests/test_auth.py turns it back on.
os.environ.setdefault("BB_AUTH", "off")
os.environ.setdefault("BB_SECRET_KEY", "test-only-secret")
