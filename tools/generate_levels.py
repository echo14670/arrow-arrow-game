"""关卡候选生成器：用「逆向摆放」构造出保证可解的布局。

原理：若某关的消除顺序是 r1, r2, ..., rn，则消除 r_i 时棋盘上还剩
r_i ... rn。于是只要按 rn, r_{n-1}, ..., r1 的顺序摆放箭头，并且摆放每
个箭头时它相对「已经摆好的箭头」前方通畅，构造出来的关卡就一定存在
r1, r2, ..., rn 这条通关路径。

用法::

    python tools/generate_levels.py --rows 4 --cols 4 --arrows 7 --mines 6 --tries 4000 --seed 1
"""

from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from game.board import Board  # noqa: E402
from game.direction import Direction  # noqa: E402
from game.solver import describe, is_solvable  # noqa: E402


def random_layout(rows: int, cols: int, arrows: int, rng: random.Random) -> Board | None:
    """按逆向摆放构造一个可解布局。"""
    board = Board.empty(rows, cols)
    cells = [(row, col) for row in range(rows) for col in range(cols)]
    rng.shuffle(cells)
    placed = 0
    for row, col in cells:
        if placed >= arrows:
            break
        directions = list(Direction)
        rng.shuffle(directions)
        for direction in directions:
            candidate = board.copy()
            candidate.place(row, col, direction)
            if candidate.is_free(row, col):
                board = candidate
                placed += 1
                break
    if placed < arrows:
        return None
    return board


def score(stats: dict[str, int], arrows: int) -> float:
    """布局评分：可解、挡住的箭头够多、需要思考的步数适中。"""
    if not stats["solvable"]:
        return -1.0
    blocked_ratio = stats["blocked_at_start"] / max(arrows, 1)
    return blocked_ratio * 2.0 + stats["choice_steps"] * 0.05 + stats["forced_steps"] * 0.1


def best_layout(
    rows: int, cols: int, arrows: int, tries: int, rng: random.Random
) -> tuple[Board, dict[str, int]]:
    best: tuple[Board, dict[str, int]] | None = None
    best_score = -1.0
    for _ in range(tries):
        board = random_layout(rows, cols, arrows, rng)
        if board is None or not is_solvable(board):
            continue
        stats = describe(board)
        current = score(stats, arrows)
        if current > best_score:
            best, best_score = (board, stats), current
    if best is None:
        raise SystemExit("生成失败：请放宽箭头数量或增加尝试次数")
    return best


def main() -> None:
    parser = argparse.ArgumentParser(description="生成可解的关卡布局")
    parser.add_argument("--rows", type=int, default=4)
    parser.add_argument("--cols", type=int, default=4)
    parser.add_argument("--arrows", type=int, default=6)
    parser.add_argument("--tries", type=int, default=3000)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--count", type=int, default=1, help="输出几个候选")
    args = parser.parse_args()

    rng = random.Random(args.seed)
    seen: set[tuple[str, ...]] = set()
    printed = 0
    while printed < args.count:
        board, stats = best_layout(args.rows, args.cols, args.arrows, args.tries, rng)
        grid = tuple(board.to_grid())
        if grid in seen:
            continue
        seen.add(grid)
        printed += 1
        print(f"# 候选 {printed} {stats} 解: {is_solvable(board)}")
        for line in board.to_grid():
            print(f'    "{line}",')


if __name__ == "__main__":
    main()