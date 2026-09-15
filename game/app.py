"""游戏主程序：初始化 pygame、事件循环与界面切换。"""

from __future__ import annotations

import os
from pathlib import Path

import pygame

from . import config
from .session import Session
from .ui import screens


class Game:
    """把窗口、时钟与界面管理器组装起来。

    ``headless=True`` 时使用 SDL 的 dummy 驱动离屏渲染，方便在没有任何
    显示器的环境下生成截图。
    """

    def __init__(self, session: Session | None = None, headless: bool = False) -> None:
        if headless:
            os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
            os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
        pygame.init()
        pygame.display.set_caption(config.WINDOW_TITLE)
        self.screen = pygame.display.set_mode((config.WINDOW_WIDTH, config.WINDOW_HEIGHT))
        self.clock = pygame.time.Clock()
        self.session = Session() if session is None else session
        self.screens = screens.ScreenManager(self.session)
        self.running = True

    def run(self) -> None:
        """主循环：处理事件、推进计时、绘制界面。"""
        try:
            while self.running:
                dt = self.clock.tick(config.FPS) / 1000.0
                self.handle_events()
                self.update(dt)
                self.draw()
                pygame.display.flip()
        finally:
            pygame.quit()

    def handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.running = False
            else:
                self.screens.handle_event(event)

    def update(self, dt: float) -> None:
        self.session.tick(dt)
        self.screens.update(dt)

    def draw(self) -> None:
        self.screens.draw(self.screen)

    def save_screenshot(self, path: str | Path) -> None:
        """把当前画面保存成 PNG。"""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.draw()
        pygame.image.save(self.screen, str(path))