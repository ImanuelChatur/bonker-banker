import sys
from pathlib import Path

# backend/ is the app root (app.py imports `routes`, `engine`, ... as top-level packages)
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
