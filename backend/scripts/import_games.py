#!/usr/bin/env python3
"""Import game JSON document(s) into a running GameGraph backend.

The backend must be running and reachable (POST /import/game). This script
only sends HTTP requests — it does not touch Neo4j directly — so all schema
and contract validation happens server-side exactly like a manual curl.

Usage:
    python scripts/import_games.py game.json
    python scripts/import_games.py app/fixtures/games/        # every *.json in the dir
    GAMEGRAPH_API=http://1.2.3.4:8100 python scripts/import_games.py games/

Environment:
    GAMEGRAPH_API   Base URL of the backend (default: http://localhost:8000)

Exit code is non-zero if any file fails to import.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

API_BASE = os.environ.get("GAMEGRAPH_API", "http://localhost:8000").rstrip("/")


def json_files(target: Path) -> list[Path]:
    if target.is_dir():
        return sorted(target.glob("*.json"))
    return [target]


def import_one(path: Path) -> tuple[bool, str]:
    request = urllib.request.Request(
        f"{API_BASE}/import/game",
        data=path.read_bytes(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = json.loads(response.read())
        return True, json.dumps(body, ensure_ascii=False)
    except urllib.error.HTTPError as exc:
        # 422 = schema invalid, 409 = contract violation (e.g. game_id mismatch)
        detail = exc.read().decode("utf-8", "replace")
        return False, f"HTTP {exc.code}: {detail}"
    except urllib.error.URLError as exc:
        return False, f"connection error ({API_BASE}): {exc.reason}"


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 2

    target = Path(argv[1])
    if not target.exists():
        print(f"path not found: {target}", file=sys.stderr)
        return 2

    files = json_files(target)
    if not files:
        print(f"no .json files in {target}", file=sys.stderr)
        return 2

    failures = 0
    for path in files:
        ok, message = import_one(path)
        print(f"[{'OK ' if ok else 'ERR'}] {path.name}: {message}")
        failures += 0 if ok else 1

    print(f"\n{len(files) - failures}/{len(files)} imported via {API_BASE}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
