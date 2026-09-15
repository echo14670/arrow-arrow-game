"""界面控件：按钮。"""

from __future__ import annotations

from typing import Callable

import pygame

from .. import config
from . import theme


class Button:
    """一个圆角按钮：支持悬停高亮与禁用状态。"""

    def __init__(
        self,
        text: str,
        rect: tuple[int, int, int, int],
        action: Callable[[], None],
        font_size: int = config.FONT_SIZE_BODY,
        primary: bool = False,
        enabled: bool = True,
    ) -> None:
        self.text = text
        self.rect = pygame.Rect(rect)
        self.action = action
        self.font_size = font_size
        self.primary = primary
        self.enabled = enabled
        self.hovered = False

    def handle_event(self, event: pygame.event.Event) -> bool:
        """处理事件；被点击且可用时返回 True。"""
        if event.type == pygame.MOUSEMOTION:
            self.hovered = self.enabled and self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.enabled and self.rect.collidepoint(event.pos):
                return True
        return False

    def draw(self, surface: pygame.Surface) -> None:
        """绘制按钮。"""
        if not self.enabled:
            background = config.COLOR_PANEL
            border = config.COLOR_BORDER
            text_color = config.COLOR_TEXT_DIM
        elif self.primary:
            background = config.COLOR_ACCENT_BRIGHT if self.hovered else config.COLOR_ACCENT
            border = config.COLOR_ACCENT_BRIGHT
            text_color = config.COLOR_BACKGROUND
        else:
            background = config.COLOR_PANEL_LIGHT if self.hovered else config.COLOR_PANEL
            border = config.COLOR_ACCENT if self.hovered else config.COLOR_BORDER
            text_color = config.COLOR_TEXT
        pygame.draw.rect(surface, background, self.rect, border_radius=12)
        pygame.draw.rect(surface, border, self.rect, width=2, border_radius=12)
        theme.draw_text(
            surface, self.text, self.font_size, text_color, center=self.rect.center
        )