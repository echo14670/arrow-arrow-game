"""动画效果：箭头飞出、碰撞抖动、浮字提示。

动画只负责绘制，棋盘状态在点击的瞬间就已经更新完毕，因此动画期间不
需要回写任何数据；但需要锁定输入，避免玩家在动画中间连续点击造成困惑。
"""

from __future__ import annotations

import math

import pygame

from .. import config
from ..direction import Direction
from . import arrow, layout


class Animation:
    """动画基类。"""

    duration: float = 0.0

    def __init__(self, start: float) -> None:
        self.start = start

    def progress(self, now: float) -> float:
        if self.duration <= 0:
            return 1.0
        return min(1.0, max(0.0, (now - self.start) / self.duration))

    def finished(self, now: float) -> bool:
        return now - self.start >= self.duration

    def draw(self, surface: pygame.Surface, now: float) -> None:  # pragma: no cover - 抽象
        raise NotImplementedError


class FlyOut(Animation):
    """箭头沿自己的方向飞出棋盘并淡出。"""

    duration = config.FLY_DURATION

    def __init__(
        self,
        start: float,
        board: pygame.Rect,
        row: int,
        col: int,
        direction: Direction,
        color: tuple[int, int, int] = config.COLOR_ACCENT,
    ) -> None:
        super().__init__(start)
        self.board = board
        self.row = row
        self.col = col
        self.direction = direction
        self.color = color

    def draw(self, surface: pygame.Surface, now: float) -> None:
        progress = self.progress(now)
        rect = layout.cell_rect(self.board, self.row, self.col)
        d_row, d_col = self.direction.delta
        distance = max(self.board.width, self.board.height) + config.CELL_SIZE
        offset = (d_col * distance * progress, d_row * distance * progress)
        image = arrow.arrow_surface(config.CELL_SIZE, self.direction, self.color).copy()
        image.set_alpha(int(255 * (1.0 - progress) ** 1.2))
        surface.blit(image, (rect.x + offset[0], rect.y + offset[1]))


class Collision(Animation):
    """被挡住：箭头左右（相对运动方向）抖动并闪红。"""

    duration = config.SHAKE_DURATION

    def __init__(
        self,
        start: float,
        board: pygame.Rect,
        row: int,
        col: int,
        direction: Direction,
    ) -> None:
        super().__init__(start)
        self.board = board
        self.row = row
        self.col = col
        self.direction = direction

    def draw(self, surface: pygame.Surface, now: float) -> None:
        progress = self.progress(now)
        rect = layout.cell_rect(self.board, self.row, self.col)
        d_row, d_col = self.direction.delta
        amplitude = config.SHAKE_AMPLITUDE * (1.0 - progress)
        offset = math.sin(progress * math.pi * 6) * amplitude
        position = (
            rect.x - d_col * offset,
            rect.y + d_row * offset,
        )
        color = config.COLOR_DANGER if progress < 0.7 else config.COLOR_ACCENT
        surface.blit(arrow.arrow_surface(config.CELL_SIZE, self.direction, color), position)


class FloatingText(Animation):
    """向上飘并淡出的提示文字。"""

    duration = config.TEXT_FLOAT_DURATION

    def __init__(
        self,
        start: float,
        text: str,
        center: tuple[int, int],
        color: tuple[int, int, int] = config.COLOR_DANGER,
        size: int = config.FONT_SIZE_BODY,
    ) -> None:
        super().__init__(start)
        self.text = text
        self.center = center
        self.color = color
        self.size = size

    def draw(self, surface: pygame.Surface, now: float) -> None:
        from . import theme

        progress = self.progress(now)
        image = theme.load_font(self.size).render(self.text, True, self.color)
        image = image.copy()
        image.set_alpha(int(255 * (1.0 - progress)))
        rect = image.get_rect(center=(self.center[0], int(self.center[1] - 34 * progress)))
        surface.blit(image, rect)


class AnimationManager:
    """统一管理当前帧的动画集合。"""

    def __init__(self) -> None:
        self.items: list[Animation] = []

    def add(self, animation: Animation) -> None:
        self.items.append(animation)

    def update(self, now: float) -> None:
        self.items = [item for item in self.items if not item.finished(now)]

    def clear(self) -> None:
        self.items.clear()

    @property
    def busy(self) -> bool:
        return bool(self.items)

    def draw(self, surface: pygame.Surface, now: float) -> None:
        for item in self.items:
            item.draw(surface, now)