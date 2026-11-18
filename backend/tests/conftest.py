import pytest

from atc.simulator.dataset import build_dataset
from atc.simulator.models import Dataset


@pytest.fixture(scope="session")
def dataset() -> Dataset:
    """The default seed-42 dataset, built once per test session."""
    return build_dataset()
