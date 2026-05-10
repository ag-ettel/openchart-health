"""Sync build/data/ -> frontend/public/data/ for local dev.

The dev server's compare page (/compare) and CompareNearbyDrawer fetch JSON
from /data/{ccn}.json, which Next.js maps to frontend/public/data/. Hospital
and nursing home pages read directly from ../build/data/ via fs.readFileSync,
so they don't need this sync — but the compare flow does.

Implementation: Windows junction if available (instant), otherwise robocopy
mirror (a few minutes for 22K files). Avoids the lengthy file-by-file copy.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path


def sync(src: Path, dest: Path) -> None:
    if not src.exists():
        print(f"Source not found: {src}", file=sys.stderr)
        sys.exit(1)

    # If dest is already a junction pointing to src, we're done.
    if dest.is_symlink() or (dest.exists() and dest.resolve() == src.resolve()):
        existing = os.readlink(dest) if dest.is_symlink() else str(dest.resolve())
        if Path(existing).resolve() == src.resolve():
            print(f"Already linked: {dest} -> {src}")
            return

    # Remove existing dest
    if dest.exists() or dest.is_symlink():
        if dest.is_symlink():
            dest.unlink()
        else:
            print(f"Removing existing {dest} ...")
            shutil.rmtree(dest)

    # Try mklink junction first (Windows, instant, no admin needed)
    if os.name == "nt":
        result = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(dest), str(src)],
            capture_output=True, text=True,
        )
        if result.returncode == 0:
            print(f"Created junction: {dest} -> {src}")
            return
        print(f"Junction failed ({result.stderr.strip()}); falling back to robocopy")

    # Fallback to robocopy mirror (Windows) or shutil.copytree
    if os.name == "nt":
        result = subprocess.run(
            ["robocopy", str(src), str(dest), "/MIR", "/MT:8", "/NFL", "/NDL", "/NP"],
            capture_output=True, text=True,
        )
        # robocopy exit codes: 0-7 are success
        if result.returncode <= 7:
            print(f"Robocopy mirrored {src} -> {dest}")
            return
        print(f"Robocopy failed: {result.stderr}", file=sys.stderr)
        sys.exit(2)

    # Non-Windows fallback
    shutil.copytree(src, dest)
    print(f"Copied {src} -> {dest}")


def main() -> int:
    repo_root = Path(__file__).parent.parent
    src = repo_root / "build" / "data"
    dest = repo_root / "frontend" / "public" / "data"
    sync(src, dest)
    files = sum(1 for _ in dest.glob("*.json"))
    print(f"frontend/public/data now has {files:,} JSON files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
