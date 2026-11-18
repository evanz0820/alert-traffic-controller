import os
import tempfile
from pathlib import Path

# Point the app at a throwaway database and rules file before any atc.db import.
_TMP = Path(tempfile.mkdtemp(prefix="atc-tests-"))
os.environ["ATC_DATABASE_URL"] = f"sqlite:///{_TMP / 'test.db'}"
os.environ["ATC_RULES_PATH"] = str(_TMP / "rules.yaml")

import pytest

from atc.simulator.dataset import build_dataset
from atc.simulator.models import Dataset


@pytest.fixture(scope="session")
def dataset() -> Dataset:
    """The default seed-42 dataset, built once per test session."""
    return build_dataset()
