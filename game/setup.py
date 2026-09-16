"""自定义关卡表单：地图大小、箭头数量与难度的取值规则。

界面只负责把这里的数值画出来，取值范围怎么夹、箭头数量上限怎么算都放在
这里，所以它不依赖 pygame，可以单独测试。
"""

from __future__ import annotations

import random

from . import generator
from .generator import Difficulty
from .levels import Level

DEFAULT_ROWS = 5
DEFAULT_COLS = 5
DEFAULT_ARROWS = 8
DEFAULT_DIFFICULTY = Difficulty.MEDIUM

FIELD_ROWS = "rows"
FIELD_COLS = "cols"
FIELD_ARROWS = "arrows"
FIELDS: tuple[str, ...] = (FIELD_ROWS, FIELD_COLS, FIELD_ARROWS)
FIELD_LABELS = {FIELD_ROWS: "行数", FIELD_COLS: "列数", FIELD_ARROWS: "箭头数量"}


class CustomSetup:
    """「自定义关卡」里用户能调的三项：地图大小、箭头数量、难度。"""

    def __init__(
        self,
        rows: int = DEFAULT_ROWS,
        cols: int = DEFAULT_COLS,
        arrows: int = DEFAULT_ARROWS,
        difficulty: Difficulty = DEFAULT_DIFFICULTY,
    ) -> None:
        self.rows = generator.clamp_size(rows)
        self.cols = generator.clamp_size(cols)
        self.arrows = generator.clamp_arrows(arrows, self.rows, self.cols)
        self.difficulty = difficulty
        self.focus_index = 0

    # ---------- 查询 ----------

    @property
    def focus(self) -> str:
        """当前被选中的字段（键盘上下键切换）。"""
        return FIELDS[self.focus_index]

    @property
    def min_size(self) -> int:
        return generator.MIN_SIZE

    @property
    def max_size(self) -> int:
        return generator.MAX_SIZE

    @property
    def min_arrows(self) -> int:
        return generator.MIN_ARROWS

    @property
    def max_arrows(self) -> int:
        """选定大小之后箭头数量的上限，也就是棋盘上的格子总数。"""
        return generator.max_arrows(self.rows, self.cols)

    @property
    def mistake_budget(self) -> int:
        """按箭头数量与难度算出来的失误次数。"""
        return generator.mistake_budget(self.arrows, self.difficulty)

    def value(self, field: str) -> int:
        """取某个字段的当前数值。"""
        if field not in FIELDS:
            raise ValueError(f"未知字段: {field!r}")
        return int(getattr(self, field))

    def limits(self, field: str) -> tuple[int, int]:
        """某个字段的 (下限, 上限)。"""
        if field == FIELD_ARROWS:
            return self.min_arrows, self.max_arrows
        return self.min_size, self.max_size

    def size_text(self) -> str:
        return f"{self.rows} × {self.cols}"

    def summary(self) -> str:
        """一行摘要，用于面板提示与测试输出。"""
        return (
            f"{self.size_text()} · {self.arrows} 箭头 · "
            f"失误 {self.mistake_budget} · {self.difficulty.label}"
        )

    # ---------- 修改 ----------

    def focus_on(self, field: str) -> None:
        if field not in FIELDS:
            raise ValueError(f"未知字段: {field!r}")
        self.focus_index = FIELDS.index(field)

    def move_focus(self, step: int) -> str:
        """换一个字段（上下键 / Tab）。"""
        self.focus_index = (self.focus_index + step) % len(FIELDS)
        return self.focus

    def set_value(self, field: str, value: int) -> bool:
        """直接给某个字段赋值（会夹到合法范围），有变化时返回 True。"""
        if field == FIELD_ROWS:
            new_rows = generator.clamp_size(value)
            changed = new_rows != self.rows
            self.rows = new_rows
        elif field == FIELD_COLS:
            new_cols = generator.clamp_size(value)
            changed = new_cols != self.cols
            self.cols = new_cols
        elif field == FIELD_ARROWS:
            new_arrows = generator.clamp_arrows(value, self.rows, self.cols)
            changed = new_arrows != self.arrows
            self.arrows = new_arrows
            return changed
        else:
            raise ValueError(f"未知字段: {field!r}")
        # 棋盘大小变了，箭头数量要跟着夹回 1 .. 行×列
        return self._clamp_arrows() or changed

    def adjust(self, delta: int, field: str | None = None) -> bool:
        """把某个字段加减 delta，夹到合法范围后返回是否发生变化。"""
        field = self.focus if field is None else field
        return self.set_value(field, self.value(field) + delta)

    def fill_arrows(self, full: bool = True) -> bool:
        """快捷：把箭头数量设成上限（full=True）或下限。"""
        return self.set_value(FIELD_ARROWS, self.max_arrows if full else self.min_arrows)

    def set_difficulty(self, difficulty: Difficulty) -> bool:
        """设置难度，档位发生变化时返回 True。"""
        if difficulty is self.difficulty:
            return False
        self.difficulty = difficulty
        return True

    def cycle_difficulty(self, step: int = 1) -> Difficulty:
        """在低/中/高之间轮流切换。"""
        order = list(Difficulty)
        self.difficulty = order[(order.index(self.difficulty) + step) % len(order)]
        return self.difficulty

    # ---------- 生成 ----------

    def build(self, rng: random.Random | None = None) -> Level:
        """按当前设置生成一个保证有解的自定义关卡。"""
        return generator.build_level(
            self.rows, self.cols, self.arrows, self.difficulty, rng
        )

    # ---------- 内部 ----------

    def _clamp_arrows(self) -> bool:
        """棋盘大小变化之后，把箭头数量夹回合法范围。"""
        clamped = generator.clamp_arrows(self.arrows, self.rows, self.cols)
        if clamped == self.arrows:
            return False
        self.arrows = clamped
        return True