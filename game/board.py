"""棋盘：二维网格上的箭头布局与路径检测。"""

from __future__ import annotations

from typing import Iterator, Sequence

from .direction import Direction

EMPTY_CHAR = "."


class Board:
    """一个关卡的全部箭头布局。

    网格用二维列表保存，每个格子是 :class:`Direction` 或 ``None``。
    """

    def __init__(self, cells: list[list[Direction | None]]) -> None:
        self._cells = cells
        self.rows = len(cells)
        self.cols = len(cells[0]) if cells else 0

    # ---------- 构造 ----------

    @classmethod
    def from_grid(cls, grid: Sequence[str]) -> "Board":
        """用关卡数据（字符串列表）构造棋盘。"""
        if not grid:
            raise ValueError("关卡数据不能为空")
        width = len(grid[0])
        if width == 0:
            raise ValueError("关卡数据不能有空行")
        cells: list[list[Direction | None]] = []
        for index, line in enumerate(grid):
            if len(line) != width:
                raise ValueError(f"第 {index + 1} 行长度与第 1 行不一致")
            row: list[Direction | None] = []
            for char in line:
                if char == EMPTY_CHAR:
                    row.append(None)
                else:
                    row.append(Direction.from_char(char))
            cells.append(row)
        return cls(cells)

    @classmethod
    def empty(cls, rows: int, cols: int) -> "Board":
        """构造一个空棋盘。"""
        return cls([[None] * cols for _ in range(rows)])

    def copy(self) -> "Board":
        return Board([list(row) for row in self._cells])

    # ---------- 查询 ----------

    def inside(self, row: int, col: int) -> bool:
        """坐标是否落在棋盘内。"""
        return 0 <= row < self.rows and 0 <= col < self.cols

    def at(self, row: int, col: int) -> Direction | None:
        """返回格子上的箭头方向，空格返回 None。"""
        if not self.inside(row, col):
            raise IndexError(f"坐标越界: ({row}, {col})")
        return self._cells[row][col]

    def has_arrow(self, row: int, col: int) -> bool:
        """格子内是否有箭头（越界视为没有）。"""
        return self.inside(row, col) and self._cells[row][col] is not None

    @property
    def arrow_count(self) -> int:
        """棋盘上剩余的箭头数量。"""
        return sum(1 for row in self._cells for cell in row if cell is not None)

    def iter_arrows(self) -> Iterator[tuple[int, int, Direction]]:
        """按行优先顺序遍历所有箭头。"""
        for row in range(self.rows):
            for col in range(self.cols):
                cell = self._cells[row][col]
                if cell is not None:
                    yield row, col, cell

    def is_free(self, row: int, col: int) -> bool:
        """判断该箭头前方到棋盘边界之间是否没有任何其他箭头。

        逐步沿箭头方向前进，一旦越界就说明前方畅通。注意这里必须显式
        判断边界，否则用负索引会绕到棋盘的另一侧，导致「向上」的箭头
        误判成被棋盘底部箭头挡住。
        """
        direction = self.at(row, col)
        if direction is None:
            return False
        d_row, d_col = direction.delta
        cur_row, cur_col = row + d_row, col + d_col
        while self.inside(cur_row, cur_col):
            if self._cells[cur_row][cur_col] is not None:
                return False
            cur_row += d_row
            cur_col += d_col
        return True

    # ---------- 修改 ----------

    def remove(self, row: int, col: int) -> Direction:
        """拿走格子中的箭头并返回它的方向。"""
        direction = self.at(row, col)
        if direction is None:
            raise ValueError(f"({row}, {col}) 上没有箭头")
        self._cells[row][col] = None
        return direction

    def place(self, row: int, col: int, direction: Direction) -> None:
        """在空格中放入箭头。"""
        if not self.inside(row, col):
            raise IndexError(f"坐标越界: ({row}, {col})")
        self._cells[row][col] = direction

    # ---------- 输出 ----------

    def to_grid(self) -> list[str]:
        """导出为关卡数据格式。"""
        return [
            "".join(EMPTY_CHAR if cell is None else cell.char for cell in row)
            for row in self._cells
        ]

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Board):
            return NotImplemented
        return self.to_grid() == other.to_grid()

    def __repr__(self) -> str:
        return "Board(\n  " + "\n  ".join(self.to_grid()) + "\n)"