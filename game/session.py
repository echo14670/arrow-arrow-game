"""游戏流程：关卡进度、失误次数、计时与撤销。"""

from __future__ import annotations

import random
from enum import Enum
from typing import Sequence

from .board import Board
from .direction import Direction
from .levels import LEVELS, Level
from .setup import CustomSetup


class Phase(Enum):
    """游戏当前所处的大阶段。"""

    START = "start"
    LEVEL_SELECT = "level_select"
    CUSTOM_SETUP = "custom_setup"
    PLAYING = "playing"
    LEVEL_CLEAR = "level_clear"
    FAILED = "failed"
    ALL_CLEAR = "all_clear"


class ClickResult(Enum):
    """一次鼠标点击的结果。"""

    REMOVED = "removed"
    BLOCKED = "blocked"
    IGNORED = "ignored"


def format_time(seconds: float) -> str:
    """把秒数格式化成 mm:ss。"""
    seconds = max(0, int(seconds))
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


class Session:
    """一次游戏过程的状态机，与界面完全解耦。"""

    def __init__(self, levels: Sequence[Level] = LEVELS) -> None:
        if not levels:
            raise ValueError("至少需要一个关卡")
        self.levels = list(levels)
        # 自定义关卡永远排在全部内置关卡后面，所以先记下内置关卡的数量
        self._builtin_count = len(self.levels)
        self.custom_setup = CustomSetup()
        self.phase = Phase.START
        self.level_index = 0
        self.level_time = 0.0
        self.total_time = 0.0
        self.level_clicks = 0
        self.level_mistakes = 0
        self.level_undos = 0
        self.level_restarts = 0
        self.total_clicks = 0
        self.total_mistakes = 0
        self.total_undos = 0
        self._cleared: set[int] = set()
        self._undo_stack: list[tuple[int, int, Direction]] = []
        self._load_level(0)

    # ---------- 查询 ----------

    @property
    def level(self) -> Level:
        return self.levels[self.level_index]

    @property
    def level_number(self) -> int:
        """当前是第几关（从 1 开始）。"""
        return self.level_index + 1

    @property
    def level_count(self) -> int:
        return len(self.levels)

    @property
    def builtin_level_count(self) -> int:
        """内置关卡的数量（自定义关卡排在它们后面）。"""
        return self._builtin_count

    @property
    def has_custom_level(self) -> bool:
        """是否已经生成过自定义关卡。"""
        return len(self.levels) > self._builtin_count

    @property
    def custom_level_index(self) -> int:
        """自定义关卡的序号；还没有生成时返回 -1。"""
        return self._builtin_count if self.has_custom_level else -1

    @property
    def is_custom_level(self) -> bool:
        """当前玩的是不是自定义关卡。"""
        return self.level_index >= self._builtin_count

    @property
    def arrows_left(self) -> int:
        return self.board.arrow_count

    @property
    def arrows_total(self) -> int:
        return self.level.arrow_count

    @property
    def mistakes_total(self) -> int:
        return self.level.mistakes

    @property
    def cleared_levels(self) -> int:
        """已经通关的关卡数量（重复通关只算一次）。"""
        return len(self._cleared)

    @property
    def can_undo(self) -> bool:
        return self.phase is Phase.PLAYING and bool(self._undo_stack)

    # ---------- 流程 ----------

    def start_game(self) -> None:
        """从开始界面进入第一关。"""
        self.start_at_level(0)

    def open_level_select(self) -> None:
        """从开始界面进入选关界面。"""
        if self.phase is not Phase.START:
            return
        self.phase = Phase.LEVEL_SELECT

    def open_custom_setup(self) -> None:
        """从选关界面进入「自定义关卡」设置面板。"""
        if self.phase is not Phase.LEVEL_SELECT:
            return
        self.phase = Phase.CUSTOM_SETUP

    def close_custom_setup(self) -> None:
        """从「自定义关卡」面板退回选关界面。"""
        if self.phase is not Phase.CUSTOM_SETUP:
            return
        self.phase = Phase.LEVEL_SELECT

    def start_custom_level(self, level: Level) -> int:
        """把生成好的关卡放进自定义关卡槽位并立刻开始，返回它的序号。

        自定义关卡只占一个槽位：再生成一次就替换掉上一次的结果。
        """
        if self.has_custom_level:
            self.levels[self._builtin_count] = level
        else:
            self.levels.append(level)
        index = self._builtin_count
        self.start_at_level(index)
        return index

    def start_generated_custom_level(self, rng: random.Random | None = None) -> int:
        """按 :attr:`custom_setup` 里的设置生成一关并开始。"""
        return self.start_custom_level(self.custom_setup.build(rng))

    def start_at_level(self, index: int) -> None:
        """从指定关卡开始新的一局（计时与统计全部重新计算）。"""
        if not 0 <= index < len(self.levels):
            raise IndexError(f"关卡序号超出范围: {index}")
        self._reset_progress()
        self._load_level(index)
        self.phase = Phase.PLAYING

    def click_cell(self, row: int, col: int) -> ClickResult:
        """点击棋盘上的一格。"""
        if self.phase is not Phase.PLAYING:
            return ClickResult.IGNORED
        if not self.board.has_arrow(row, col):
            return ClickResult.IGNORED
        self.level_clicks += 1
        self.total_clicks += 1
        if self.board.is_free(row, col):
            direction = self.board.remove(row, col)
            self._undo_stack.append((row, col, direction))
            if self.board.arrow_count == 0:
                self._on_level_cleared()
            return ClickResult.REMOVED
        self.mistakes_left -= 1
        self.level_mistakes += 1
        self.total_mistakes += 1
        if self.mistakes_left <= 0:
            self.mistakes_left = 0
            self.phase = Phase.FAILED
        return ClickResult.BLOCKED

    def undo(self) -> bool:
        """撤销上一次成功消除；不消耗失误、不回退计时。"""
        if not self.can_undo:
            return False
        row, col, direction = self._undo_stack.pop()
        self.board.place(row, col, direction)
        self.level_undos += 1
        self.total_undos += 1
        return True

    def restart_level(self) -> None:
        """把当前关卡恢复到初始状态（箭头布局与失误次数都还原）。"""
        if self.phase not in (Phase.PLAYING, Phase.LEVEL_CLEAR, Phase.FAILED):
            return
        self.level_restarts += 1
        self._load_level(self.level_index)
        self.phase = Phase.PLAYING

    def next_level(self) -> bool:
        """进入下一关；已经是最后一关时切到全部通关界面。"""
        if self.phase is not Phase.LEVEL_CLEAR:
            return False
        if self.level_index + 1 >= len(self.levels):
            self.phase = Phase.ALL_CLEAR
            return False
        self._load_level(self.level_index + 1)
        self.phase = Phase.PLAYING
        return True

    def back_to_menu(self) -> None:
        """回到开始界面并重置进度。"""
        self._reset_progress()
        self._load_level(0)
        self.phase = Phase.START

    def tick(self, dt: float) -> None:
        """推进计时。"""
        if self.phase is Phase.PLAYING:
            dt = max(0.0, float(dt))
            self.level_time += dt
            self.total_time += dt

    # ---------- 统计 ----------

    def summary(self) -> dict[str, float | int]:
        """汇总一局数据，供结果界面与博客记录使用。"""
        return {
            "cleared_levels": self.cleared_levels,
            "level_count": self.level_count,
            "total_clicks": self.total_clicks,
            "total_mistakes": self.total_mistakes,
            "total_undos": self.total_undos,
            "total_time": round(self.total_time, 1),
        }

    # ---------- 内部 ----------

    def _reset_progress(self) -> None:
        """把一局的统计清零（选关重开时也要复位）。"""
        self._cleared.clear()
        self.total_time = 0.0
        self.total_clicks = 0
        self.total_mistakes = 0
        self.total_undos = 0
        self.level_restarts = 0

    def _load_level(self, index: int) -> None:
        level = self.levels[index]
        self.level_index = index
        self.board = Board.from_grid(level.grid)
        self.mistakes_left = level.mistakes
        self.level_time = 0.0
        self.level_clicks = 0
        self.level_mistakes = 0
        self.level_undos = 0
        self._undo_stack.clear()

    def _on_level_cleared(self) -> None:
        self._cleared.add(self.level_index)
        self.phase = Phase.LEVEL_CLEAR