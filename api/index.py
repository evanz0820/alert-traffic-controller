"""Vercel Python function: serves the ATC FastAPI app for every /api/* request.

vercel.json rewrites /api/(.*) here; FastAPI receives the original path, and all of its
routes live under /api. The app reads the committed snapshot backend/data/atc.db
read-only, so the function needs no writable storage.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend" / "src"))

from atc.api.main import app  # noqa: E402

__all__ = ["app"]
