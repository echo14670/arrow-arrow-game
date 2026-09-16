"""配色与字体。

字体按 Windows 常见中文字体顺序回退：先用字体文件（避免 SysFont 名称
匹配失败），再尝试系统字体名，最后退回 pygame 内置字体。
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import pygame

from .. import config


@lru_cache(maxsize=None)
def load_font(size: int) -> pygame.font.Font:
    """按字号加载中文字体（结果会被缓存）。"""
    for candidate in config.FONT_CANDIDATES:
        if Path(candidate).exists():
            try:
                return pygame.font.Font(candidate, size)
            except OSError:
                continue
    for name in config.SYS_FONT_CANDIDATES:
        match = pygame.font.match_font(name)
        if match:
            try:
                return pygame.font.Font(match, size)
            except OSError:
                continue
    return pygame.font.Font(None, size)


def clear_cache() -> None:
    """丢弃缓存的字体对象。

    pygame 重新初始化（quit 后再 init）之后，之前缓存的 Font 会引用已经
    释放的底层资源，继续使用会导致访问违例，因此必须清空缓存。
    """
    load_font.cache_clear()


def draw_text(
    surface: pygame.Surface,
    text: str,
    size: int,
    color: tuple[int, int, int],
    topleft: tuple[int, int] | None = None,
    center: tuple[int, int] | None = None,
    topright: tuple[int, int] | None = None,
    centerx: int | None = None,
    top: int | None = None,
) -> pygame.Rect:
    """绘制一行文字并返回它的矩形。"""
    image = load_font(size).render(text, True, color)
    rect = image.get_rect()
    if topleft is not None:
        rect.topleft = topleft
    if topright is not None:
        rect.topright = topright
    if center is not None:
        rect.center = center
    if centerx is not None:
        rect.centerx = centerx
    if top is not None:
        rect.top = top
    surface.blit(image, rect)
    return rect