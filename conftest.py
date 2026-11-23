"""Marks tests by what they need, so CI and `make` can pick them:

    python -m pytest -m "not db and not slow"   # fast, no database
    python -m pytest -m db                      # needs Postgres
    python -m pytest -m slow                    # the generator's tests

`db`: the test uses the `conn` fixture (directly or through another
fixture), so it needs a Postgres test database (RX_TEST_DSN).
`slow`: the dataset generator's tests, which build worlds or render
files and take minutes (CI runs them weekly)."""
import fnmatch

import pytest

DB_FIXTURES = {"conn"}
DB_MODULES = {"test_db.py"}       # connects without the fixture
SLOW_MODULES = ("test_gen_*.py", "test_golden.py", "test_querylog.py",
                "test_render_*.py", "test_data_tarnwick.py")


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "db: needs a Postgres test database (RX_TEST_DSN)")
    config.addinivalue_line(
        "markers", "slow: the dataset generator's tests (minutes)")


def pytest_collection_modifyitems(items):
    for item in items:
        names = set(getattr(item, "fixturenames", ()))
        if names & DB_FIXTURES or item.path.name in DB_MODULES:
            item.add_marker(pytest.mark.db)
        if any(fnmatch.fnmatch(item.path.name, p) for p in SLOW_MODULES):
            item.add_marker(pytest.mark.slow)
