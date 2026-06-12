#!/usr/bin/env python3
"""清空 Neo4j 图谱并用 fixtures 重新灌入全部种子游戏（直连 Neo4j）。

与 import_games.py（走 HTTP /import/game）不同，本脚本**直接连 Neo4j**：先
`MATCH (n) DETACH DELETE n` 清空整图，再用当前 schema 校验（validate_import_document）
后 upsert 每个 app/fixtures/games/*.json。用于架构/schema 变动后刷新旧数据：
重置 document_json 为当前 schema、补齐全维度边（含 theme/game_feel）、清掉残留旧属性。

破坏性操作：会删除整个图。必须显式传 --wipe 才执行。

用法：
    NEO4J_PASSWORD=... python scripts/reseed_games.py --wipe
    NEO4J_URI=bolt://host:7687 NEO4J_USER=neo4j NEO4J_PASSWORD=... \
        python scripts/reseed_games.py --wipe [games-dir]

环境变量：
    NEO4J_URI       默认 bolt://localhost:7687
    NEO4J_USER      默认 neo4j
    NEO4J_PASSWORD  必填

任一文件导入失败则退出码非 0。
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from neo4j import Driver

from app.graph.connection import Neo4jSettings, create_driver
from app.graph.game_repository import GameRepository
from app.services.import_service import validate_import_document

_DEFAULT_GAMES = Path(__file__).resolve().parents[1] / "app" / "fixtures" / "games"


def wipe_graph(driver: Driver) -> int:
    """删除全部节点与关系，返回删除的节点数。"""
    with driver.session() as session:
        summary = session.run("MATCH (n) DETACH DELETE n").consume()
    return summary.counters.nodes_deleted


def reseed(driver: Driver, files: list[Path]) -> tuple[int, int]:
    """按当前 schema 校验并 upsert 每个 fixture；返回 (成功数, 总数)。"""
    repo = GameRepository(driver)
    ok = 0
    for path in files:
        try:
            document = validate_import_document(
                json.loads(path.read_text(encoding="utf-8"))
            )
            repo.upsert_game(document)
            print(f"[OK ] {path.name}")
            ok += 1
        except Exception as exc:  # noqa: BLE001 - 报告并继续，最后用退出码反映失败
            print(f"[ERR] {path.name}: {exc}")
    return ok, len(files)


def main(argv: list[str]) -> int:
    args = argv[1:]
    if "--wipe" not in args:
        print(__doc__)
        print("拒绝执行：清空是破坏性操作，必须显式传 --wipe。", file=sys.stderr)
        return 2

    positional = [a for a in args if not a.startswith("--")]
    games_dir = Path(positional[0]) if positional else _DEFAULT_GAMES
    if not games_dir.exists():
        print(f"目录不存在：{games_dir}", file=sys.stderr)
        return 2
    files = sorted(games_dir.glob("*.json"))
    if not files:
        print(f"{games_dir} 下没有 .json", file=sys.stderr)
        return 2

    if not os.environ.get("NEO4J_PASSWORD"):
        print("缺少 NEO4J_PASSWORD 环境变量。", file=sys.stderr)
        return 2

    settings = Neo4jSettings.from_env()
    driver = create_driver(settings)
    try:
        print(f"目标 Neo4j：{settings.uri}（user={settings.user}）")
        print("清空图谱…")
        deleted = wipe_graph(driver)
        print(f"  已删除 {deleted} 个节点")
        print(f"重新灌入 {len(files)} 个游戏…")
        ok, total = reseed(driver, files)
        print(f"\n完成：{ok}/{total} 个游戏已重灌至 {settings.uri}")
        return 0 if ok == total else 1
    finally:
        driver.close()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
