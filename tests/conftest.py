"""Shared fixtures: the corpus on disk and a fresh test database."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from rx import config, db

ROOT = Path(__file__).resolve().parent.parent


def load_script(name: str):
    """Import scripts/<name>.py, which is not part of the package."""
    path = ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="session")
def make_corpus():
    return load_script("make_corpus")


@pytest.fixture(scope="session")
def corpus_dir(tmp_path_factory, make_corpus) -> Path:
    """The generated corpus; built into a temp dir if missing."""
    if (config.CORPUS_DIR / "manifest.jsonl").exists():
        return config.CORPUS_DIR
    out = tmp_path_factory.mktemp("corpus")
    make_corpus.generate(out)
    return out


@pytest.fixture
def conn():
    """A connection to rx_test with an empty, freshly built schema."""
    connection = db.connect(config.TEST_DSN)
    db.reset_schema(connection)
    yield connection
    connection.close()
