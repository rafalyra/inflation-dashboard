"""Save raw responses exactly as received, with a record of where and when they came from.

Keeping the untouched bytes means any published number can be traced back to what the
agency returned, and normalization can be re-run without hitting the network.

Each raw file `x.json` gets a sidecar `x.json.meta` holding its URL and fetch time. One
sidecar per file (rather than one shared manifest) means two fetches running at the same
time can't overwrite each other's records.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

META_SUFFIX = ".meta"
LEGACY_MANIFEST = "manifest.json"  # older layout, still read as a fallback


class RawStore:
    def __init__(self, root: Path) -> None:
        self.root = root

    def save(self, name: str, content: bytes, url: str) -> Path:
        """Write `content` to `<root>/<name>` and record its URL and fetch time beside it."""
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        meta = {"url": url, "fetched_at_utc": datetime.now(UTC).isoformat()}
        Path(f"{path}{META_SUFFIX}").write_text(json.dumps(meta, indent=1), "utf-8")
        return path

    def meta(self, name: str) -> dict[str, str]:
        sidecar = Path(f"{self.root / name}{META_SUFFIX}")
        if sidecar.exists():
            data: dict[str, str] = json.loads(sidecar.read_text("utf-8"))
            return data
        legacy = self.root / LEGACY_MANIFEST
        if legacy.exists():
            manifest: dict[str, dict[str, str]] = json.loads(legacy.read_text("utf-8"))
            if name in manifest:
                return manifest[name]
        raise KeyError(f"no fetch record for raw file {name}")

    def fetched_at(self, name: str) -> datetime:
        return datetime.fromisoformat(self.meta(name)["fetched_at_utc"])

    def files(self, pattern: str) -> list[Path]:
        return sorted(p for p in self.root.glob(pattern) if not p.name.endswith(META_SUFFIX))

    def read_json(self, path: Path) -> object:
        return json.loads(path.read_text("utf-8"))
