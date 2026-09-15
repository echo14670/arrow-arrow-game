"""关卡数据。

布局用等长字符串表示：``.`` 表示空格，``^ v < >`` 表示四种方向的箭头。
每个关卡都经过 :func:`game.solver.solve` 校验，保证存在完整通关顺序。
"""

from __future__ import annotations

from dataclasses import dataclass

EMPTY_CHAR = "."


@dataclass(frozen=True)
class Level:
    """一个关卡的初始布局与失误次数上限。"""

    name: str
    grid: tuple[str, ...]
    mistakes: int

    @property
    def rows(self) -> int:
        return len(self.grid)

    @property
    def cols(self) -> int:
        return len(self.grid[0]) if self.grid else 0

    @property
    def arrow_count(self) -> int:
        """关卡初始的箭头总数。"""
        return sum(1 for line in self.grid for char in line if char != EMPTY_CHAR)


LEVELS: tuple[Level, ...] = (
    Level(
        name="第 1 关 · 认识箭头",
        grid=(
            ".>.",
            "..v",
            ".^.",
        ),
        mistakes=5,
    ),
    Level(
        name="第 2 关 · 错身而过",
        grid=(
            ".v..",
            ">>vv",
            "....",
            "...<",
        ),
        mistakes=4,
    ),
    Level(
        name="第 3 关 · 同列成串",
        grid=(
            ">.>>",
            "....",
            "^.^^",
            ".>.>",
        ),
        mistakes=4,
    ),
    Level(
        name="第 4 关 · 层层叠叠",
        grid=(
            ".....",
            "^.<..",
            "^....",
            "^<^.v",
            ".v.<<",
        ),
        mistakes=3,
    ),
    Level(
        name="第 5 关 · 交错迷阵",
        grid=(
            ".<v..",
            ".^v^.",
            "...^>",
            "v^.^.",
            "v.<..",
        ),
        mistakes=3,
    ),
    Level(
        name="第 6 关 · 终局考验",
        grid=(
            "....v.",
            "<.<..v",
            "..>.>v",
            "^v....",
            "v.v...",
            ".<>.>>",
        ),
        mistakes=3,
    ),
)

NUM_LEVELS = len(LEVELS)