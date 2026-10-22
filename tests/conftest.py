from pathlib import Path

import httpx
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def repo_config_dir() -> Path:
    return REPO_ROOT / "config"


@pytest.fixture(autouse=True)
def _no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    """Tests never call the network (CLAUDE.md). Any attempt fails loudly instead."""

    def refuse(*args: object, **kwargs: object) -> None:
        raise RuntimeError("tests must not use the network; record a fixture instead")

    monkeypatch.setattr(httpx.Client, "send", refuse)
