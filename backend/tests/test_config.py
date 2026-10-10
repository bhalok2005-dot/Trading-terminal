import pytest

from backend.app.config import Settings


@pytest.mark.parametrize(
    ("database_url", "expected"),
    [
        ("postgres://user:pass@host:5432/db", "postgresql+psycopg://user:pass@host:5432/db"),
        ("postgresql://user:pass@host:5432/db", "postgresql+psycopg://user:pass@host:5432/db"),
        ("sqlite:///./trading_dashboard.db", "sqlite:///./trading_dashboard.db"),
    ],
)
def test_database_url_uses_supported_driver(database_url: str, expected: str) -> None:
    assert Settings(DATABASE_URL=database_url).DATABASE_URL == expected