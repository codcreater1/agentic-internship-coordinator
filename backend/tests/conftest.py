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
from app.services import report_repository  # noqa: E402

_TEST_ROOT = Path(tempfile.mkdtemp(prefix="aic-test-"))
settings.db_path = _TEST_ROOT / "test.db"

# Task directories hold submitted attachments and generated certificates. Point
# them at the same temp root so a test run leaves nothing in the working tree.
settings.storage_root = _TEST_ROOT / "tasks"

# Both tables, because tests construct TestClient(app) at module level, which
# does not run the lifespan hook that would otherwise create them.
repo.init_db()
report_repository.init_db()
