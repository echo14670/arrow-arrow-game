"""箭头绘制：用多边形画出四种方向的箭头，并按（方向, 尺寸, 颜色）缓存。"""

from __future__ import annotations

from functools import lru_cache

import pygame

from ..direction import Direction

# 以「朝右」为基准的箭头轮廓，坐标是相对格子尺寸的比例
_BASE_POINTS = (
    (-0.34, -0.12),
    (0.10, -0.12),
    (0.10, -0.30),
    (0.38, 0.00),
    (0.10, 0.30),
    (0.10, 0.12),
    (-0.34, 0.12),
)

_ANGLE = {
    Direction.RIGHT: 0,
    Direction.DOWN: 90,
    Direction.LEFT: 180,
    Direction.UP: 270,
}


def arrow_points(size: int, direction: Direction) -> list[tuple[float, float]]:
    """给定格子尺寸与方向，返回箭头的多边形顶点。"""
    center = pygame.math.Vector2(size / 2, size / 2)
    scale = size * 0.5
    angle = _ANGLE[direction]
    points = []
    for ratio_x, ratio_y in _BASE_POINTS:
        vector = pygame.math.Vector2(ratio_x * scale, ratio_y * scale)
        vector = vector.rotate(angle)
        points.append((center.x + vector.x, center.y + vector.y))
    return points


def clear_cache() -> None:
    """丢弃缓存的箭头贴图（pygame 重新初始化后必须调用）。"""
    arrow_surface.cache_clear()


@lru_cache(maxsize=64)
def arrow_surface(
    size: int, direction: Direction, color: tuple[int, int, int]
) -> pygame.Surface:
    """渲染一个箭头到透明表面（带缓存）。"""
    surface = pygame.Surface((size, size), pygame.SRCALPHA)
    pygame.draw.polygon(surface, color, arrow_points(size, direction))
    return surface