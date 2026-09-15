"""打印各关卡的统计数据，便于填写 README 与博客中的关卡表格。

    python tools/level_stats.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from game.board import Board  # noqa: E402
from game.levels import LEVELS  # noqa: E402
from game.solver import describe, solve  # noqa: E402


def main() -> None:
    total = 0
    print("关卡\t名称\t尺寸\t箭头数\t初始被挡\t必经步\t可选步\t失误上限")
    for index, level in enumerate(LEVELS, start=1):
        board = Board.from_grid(level.grid)
        stats = describe(board)
        total += stats["arrow_count"]
        print(
            f"{index}\t{level.name}\t{level.rows}x{level.cols}\t"
            f"{stats['arrow_count']}\t{stats['blocked_at_start']}\t"
            f"{stats['forced_steps']}\t{stats['choice_steps']}\t{level.mistakes}"
        )
        assert len(solve(board)) == stats["arrow_count"], "关卡无解"
    print(f"箭头总数: {total}")


if __name__ == "__main__":
    main()