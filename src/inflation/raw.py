"""Save raw responses exactly as received, with a manifest of where and when they came from.

Keeping the untouched bytes means any published number can be traced back to what the
agency returned, and normalization can be re-run without hitting the network.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

MANIFEST = "manifest.json"


class RawStore:
    def __init__(self, root: Path) -> None:
        self.root = root

    def save(self, name: str, content: bytes, url: str) -> Path:
        """Write `content` to `<root>/<name>` and record its URL and fetch time."""
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        manifest = self.manifest()
        manifest[name] = {"url": url, "fetched_at_utc": datetime.now(UTC).isoformat()}
        (self.root / MANIFEST).write_text(json.dumps(manifest, indent=1, sort_keys=True), "utf-8")
        return path

    def manifest(self) -> dict[str, dict[str, str]]:
        path = self.root / MANIFEST
        if not path.exists():
            return {}
        data: dict[str, dict[str, str]] = json.loads(path.read_text("utf-8"))
        return data

    def fetched_at(self, name: str) -> datetime:
        return datetime.fromisoformat(self.manifest()[name]["fetched_at_utc"])

    def files(self, pattern: str) -> list[Path]:
        return sorted(self.root.glob(pattern))

    def read_json(self, path: Path) -> object:
        return json.loads(path.read_text("utf-8"))
