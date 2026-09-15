"""方向定义：四种箭头方向及其在网格中的位移。"""

from __future__ import annotations

from enum import Enum


class Direction(Enum):
    """箭头方向。

    value 为 (行增量, 列增量)：行号向下增长，列号向右增长。
    """

    UP = (-1, 0)
    DOWN = (1, 0)
    LEFT = (0, -1)
    RIGHT = (0, 1)

    @property
    def delta(self) -> tuple[int, int]:
        """返回该方向对应的 (行增量, 列增量)。"""
        return self.value

    @property
    def char(self) -> str:
        """关卡数据中用来表示该方向的字符。"""
        return _CHAR[self]

    @property
    def label(self) -> str:
        """中文名称，用于界面提示。"""
        return _LABEL[self]

    @classmethod
    def from_char(cls, char: str) -> "Direction":
        """把关卡数据中的字符解析为方向。"""
        try:
            return _FROM_CHAR[char]
        except KeyError:
            raise ValueError(f"无法识别的箭头字符: {char!r}") from None


_CHAR = {
    Direction.UP: "^",
    Direction.DOWN: "v",
    Direction.LEFT: "<",
    Direction.RIGHT: ">",
}
_FROM_CHAR = {char: direction for direction, char in _CHAR.items()}
_LABEL = {
    Direction.UP: "上",
    Direction.DOWN: "下",
    Direction.LEFT: "左",
    Direction.RIGHT: "右",
}