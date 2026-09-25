import json
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def healthy_report() -> dict:
    return json.loads((FIXTURES / "healthy_host.json").read_text())


@pytest.fixture
def sick_report() -> dict:
    return json.loads((FIXTURES / "sick_host.json").read_text())


@pytest.fixture
def db_path(tmp_path) -> str:
    return str(tmp_path / "test.db")
