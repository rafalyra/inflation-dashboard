"""Download the US Census Bureau's X-13ARIMA-SEATS binary into tools/x13/.

    uv run python scripts/install_x13.py

The pipeline uses it for seasonal adjustment (src/inflation/metrics/seasonal.py). Without
it, everything else still works and the momentum charts say adjustment is unavailable.
Archive URLs verified 2026-10-22 (build b62, "ascii" output variant).
"""

from __future__ import annotations

import io
import platform
import stat
import tarfile
import zipfile
from pathlib import Path

import httpx

BASE = "https://www2.census.gov/software/x-13arima-seats/x13as"
ARCHIVES = {
    "Windows": f"{BASE}/windows/program-archives/x13as_ascii-v1-1-b62.zip",
    "Linux": f"{BASE}/unix-linux/program-archives/x13as_ascii-v1-1-b62.tar.gz",
}
TARGET = Path("tools/x13")


def main() -> None:
    system = platform.system()
    if system not in ARCHIVES:
        raise SystemExit(f"No Census X-13 build for {system}; set X13PATH to your own binary.")
    url = ARCHIVES[system]
    print(f"Downloading {url}")
    data = httpx.get(url, timeout=120, follow_redirects=True).raise_for_status().content
    TARGET.mkdir(parents=True, exist_ok=True)
    name = "x13as.exe" if system == "Windows" else "x13as"
    if url.endswith(".zip"):
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            member = next(m for m in archive.namelist() if m.lower().endswith("x13as_ascii.exe"))
            (TARGET / name).write_bytes(archive.read(member))
    else:
        with tarfile.open(fileobj=io.BytesIO(data)) as archive:
            member = next(m for m in archive.getmembers() if m.name.endswith("x13as_ascii"))
            extracted = archive.extractfile(member)
            assert extracted is not None
            (TARGET / name).write_bytes(extracted.read())
    path = TARGET / name
    path.chmod(path.stat().st_mode | stat.S_IEXEC)
    print(f"Installed {path}")


if __name__ == "__main__":
    main()
