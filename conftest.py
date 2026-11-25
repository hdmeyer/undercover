import pytest


@pytest.fixture(autouse=True)
def database(tmp_path, monkeypatch):
    """Give every test its own database, so no test touches undercover.db."""
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "test.db"))
