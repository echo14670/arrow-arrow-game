"""随机关卡生成器：生成的自定义关卡一定有解。

这里提供两种构造方式：

1. **随机摆放**（:func:`random_layout`）：随机挑格子与方向，只要求新箭头相对
   已经摆好的箭头前方通畅。由于摆放顺序就是消除顺序的逆序，摆出来的关卡一定
   可解；但这种做法能不能摆满指定数量要看运气。
2. **洋葱式摆放**（:func:`onion_layout`）：按「离最近的边有多远」给格子分层，
   从内层往外层逆向摆放，每个箭头指向最近的边（或者任何前方没有更内层箭头的
   方向）。一个箭头指向最近的边时，它前方只可能是更外圈的格子，而那些箭头会
   更早被消除，所以这种方式**在 1 .. 行×列 的任意数量下都能构造出可解关卡**，
   用来兜住所有高密度的情况。

难度用 :func:`score` 衡量：开局被挡住的箭头比例越高、需要做选择的步数越多，分数
越高。高难度取分数最高的候选，低难度取最低的，中档取中位数。
"""

from __future__ import annotations

import random
from enum import Enum

from . import config
from .board import Board
from .direction import Direction
from .levels import Level
from .solver import describe, is_solvable

# 棋盘大小范围：上限沿用界面按 6x6 设计的最大棋盘，下限取 2 避免退化成一行
MIN_SIZE = 2
MAX_SIZE = config.BOARD_MAX_SIZE

MIN_ARROWS = 1

# 自定义关卡的失误次数 = 箭头数 × 比例（再夹到 2..8）
MISTAKE_RATIO = {"low": 0.5, "medium": 0.35, "high": 0.25}
MIN_MISTAKES = 2
MAX_MISTAKES = 8

DEFAULT_CANDIDATES = 24


class Difficulty(Enum):
    """难度档位。"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

    @property
    def label(self) -> str:
        return {"low": "低难度", "medium": "中难度", "high": "高难度"}[self.value]


# ---------- 参数范围 ----------


def clamp_size(value: int) -> int:
    """把行数/列数夹到允许范围内。"""
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = MIN_SIZE
    return max(MIN_SIZE, min(MAX_SIZE, number))


def max_arrows(rows: int, cols: int) -> int:
    """理论上限：每个格子都能放一个箭头。

    洋葱式摆放能保证任意数量都能构造出可解关卡，所以上限就是格子的总数。
    """
    rows, cols = clamp_size(rows), clamp_size(cols)
    return rows * cols


def clamp_arrows(value: int, rows: int, cols: int) -> int:
    """把箭头数量夹到 1 .. 行×列。"""
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = MIN_ARROWS
    return max(MIN_ARROWS, min(max_arrows(rows, cols), number))


def mistake_budget(arrows: int, difficulty: Difficulty) -> int:
    """根据箭头数量与难度给出失误次数上限。"""
    ratio = MISTAKE_RATIO[difficulty.value]
    return max(MIN_MISTAKES, min(MAX_MISTAKES, round(arrows * ratio)))


# ---------- 评分 ----------


def score(board: Board) -> float:
    """给一个布局打分，分数越高表示越难。

    由三部分组成：开局被挡住的箭头比例（权重最高）、有多个选择的步数、
    只有唯一选择的步数。不可解的布局返回 -1。
    """
    stats = describe(board)
    if not stats["solvable"]:
        return -1.0
    blocked_ratio = stats["blocked_at_start"] / max(stats["arrow_count"], 1)
    return blocked_ratio * 2.0 + stats["choice_steps"] * 0.05 + stats["forced_steps"] * 0.1


# ---------- 构造 ----------


def _ring(row: int, col: int, rows: int, cols: int) -> int:
    """格子到最近一条边的距离（第几层「洋葱皮」）。"""
    return min(row, col, rows - 1 - row, cols - 1 - col)


def _place_randomly(rows: int, cols: int, arrows: int, rng: random.Random) -> Board | None:
    """随机摆放一次，摆满 arrows 个箭头就返回棋盘，否则返回 None。"""
    board = Board.empty(rows, cols)
    cells = [(row, col) for row in range(rows) for col in range(cols)]
    rng.shuffle(cells)
    placed = 0
    for row, col in cells:
        if placed >= arrows:
            break
        candidates = list(Direction)
        rng.shuffle(candidates)
        for direction in candidates:
            trial = board.copy()
            trial.place(row, col, direction)
            if trial.is_free(row, col):
                board = trial
                placed += 1
                break
    return board if placed == arrows else None


def random_layout(
    rows: int, cols: int, arrows: int, rng: random.Random, attempts: int = 8
) -> Board | None:
    """多次尝试随机摆放，摆不满指定数量时返回 None。"""
    for _ in range(attempts):
        board = _place_randomly(rows, cols, arrows, rng)
        if board is not None:
            return board
    return None


def onion_layout(rows: int, cols: int, arrows: int, rng: random.Random) -> Board:
    """洋葱式摆放：任意 1 .. 行×列 的箭头数量都能构造出可解关卡。"""
    rows, cols = clamp_size(rows), clamp_size(cols)
    arrows = clamp_arrows(arrows, rows, cols)
    cells = [(row, col) for row in range(rows) for col in range(cols)]
    rng.shuffle(cells)
    chosen = cells[:arrows]
    # 消除顺序：先外圈后内圈（同层随机）
    order = sorted(chosen, key=lambda cell: (_ring(cell[0], cell[1], rows, cols), rng.random()))
    board = Board.empty(rows, cols)
    for row, col in reversed(order):  # 逆向摆放：越晚消除的越先放
        candidates = list(Direction)
        rng.shuffle(candidates)
        for direction in candidates:
            trial = board.copy()
            trial.place(row, col, direction)
            if trial.is_free(row, col):
                board = trial
                break
        else:  # pragma: no cover - 指向最近的边必然可行
            raise RuntimeError("洋葱式摆放失败，这不应该发生")
    return board


def generate(
    rows: int,
    cols: int,
    arrows: int,
    difficulty: Difficulty = Difficulty.MEDIUM,
    rng: random.Random | None = None,
    candidates: int = DEFAULT_CANDIDATES,
) -> Board:
    """生成一个「箭头数量正确且一定有解」的棋盘，并按难度挑选候选。"""
    rows, cols = clamp_size(rows), clamp_size(cols)
    arrows = clamp_arrows(arrows, rows, cols)
    rng = rng or random.Random()

    pool: list[tuple[float, Board]] = []
    for _ in range(max(1, candidates)):
        board = random_layout(rows, cols, arrows, rng)
        if board is None:
            board = onion_layout(rows, cols, arrows, rng)
        if board.arrow_count != arrows or not is_solvable(board):
            continue
        pool.append((score(board), board))
    if not pool:  # pragma: no cover - 洋葱式摆放兜底
        board = onion_layout(rows, cols, arrows, rng)
        pool.append((score(board), board))

    pool.sort(key=lambda item: item[0])
    if difficulty is Difficulty.HIGH:
        return pool[-1][1]
    if difficulty is Difficulty.LOW:
        return pool[0][1]
    return pool[len(pool) // 2][1]


def build_level(
    rows: int,
    cols: int,
    arrows: int,
    difficulty: Difficulty = Difficulty.MEDIUM,
    rng: random.Random | None = None,
) -> Level:
    """生成一个可以直接交给 :class:`~game.session.Session` 的自定义关卡。"""
    board = generate(rows, cols, arrows, difficulty, rng)
    rows, cols = clamp_size(rows), clamp_size(cols)
    return Level(
        name=f"自定义关卡 · {difficulty.label}",
        grid=tuple(board.to_grid()),
        mistakes=mistake_budget(board.arrow_count, difficulty),
    )