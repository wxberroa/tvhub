import os
import sys
import tempfile
from pathlib import Path

# DATA_DIR is read at import time, so point it at a scratch dir before importing the app.
os.environ["DATA_DIR"] = tempfile.mkdtemp(prefix="tvhub-test-")
for k in ("TVHUB_AUTH", "SUPERVISOR_TOKEN", "TVHUB_TOKEN", "TVDECK_TOKEN"):
    os.environ.pop(k, None)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))
