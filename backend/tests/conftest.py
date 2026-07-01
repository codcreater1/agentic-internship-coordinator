"""Test setup: force offline (fallback) mode and an isolated temp database.

Runs at conftest import time — before test modules import the app — so the
settings are in place before `app.main` calls `load_dotenv()`.
"""

import os
import tempfile
from pathlib import Path

# Force the keyword fallback so tests are hermetic and never hit the network.
os.environ["LLM_API_KEY"] = ""

from app.core.config import settings  # noqa: E402
from app.services import application_repository as repo  # noqa: E402

settings.db_path = Path(tempfile.mkdtemp(prefix="aic-test-")) / "test.db"
repo.init_db()
