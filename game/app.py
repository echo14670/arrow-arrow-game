"""游戏主程序：初始化 pygame、事件循环与界面切换。

窗口按「逻辑分辨率 + 缩放显示」创建：所有界面始终绘制在
``config.WINDOW_WIDTH x config.WINDOW_HEIGHT`` 的逻辑画面上，由 pygame 的
``SCALED`` 标志放大到实际窗口或全屏，鼠标坐标也会被自动换算回逻辑坐标，
因此界面代码不需要感知窗口大小。全屏用 ``display.toggle_fullscreen()``
切换，它不重建窗口与渲染器，可以反复来回切换。
"""

from __future__ import annotations

import os
from pathlib import Path

import pygame

from . import config
from .session import Session
from .ui import arrow, screens, theme


class Game:
    """把窗口、时钟与界面管理器组装起来。

    ``headless=True`` 时使用 SDL 的 dummy 驱动离屏渲染，方便在没有任何
    显示器的环境下生成截图。
    """

    def __init__(self, session: Session | None = None, headless: bool = False) -> None:
        self.headless = headless
        self.fullscreen = False
        if headless:
            os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
            os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
        else:
            # 让窗口使用物理像素：否则高 DPI 屏幕上全屏画面会被系统整体拉伸，
            # 既模糊，拿到的窗口尺寸也不是屏幕真实分辨率
            os.environ.setdefault("SDL_WINDOWS_DPI_AWARENESS", "permonitorv2")
        pygame.init()
        # pygame 重新初始化后，上一轮会话缓存的字体与贴图会引用已释放的资源，
        # 继续使用会导致进程崩溃（访问违例），所以这里先丢弃它们
        theme.clear_cache()
        arrow.clear_cache()
        pygame.display.set_caption(config.WINDOW_TITLE)
        self.screen = pygame.display.set_mode(
            (config.WINDOW_WIDTH, config.WINDOW_HEIGHT), self.window_flags()
        )
        self.clock = pygame.time.Clock()
        self.session = Session() if session is None else session
        self.screens = screens.ScreenManager(self.session)
        self.running = True

    # ------------------------------------------------------------------ 窗口
    def window_flags(self) -> int:
        """窗口模式下的显示标志。

        ``SCALED`` 让逻辑分辨率固定、由 SDL 负责缩放到窗口或全屏；
        ``RESIZABLE`` 允许拖动窗口边缘或点最大化。``headless`` 下不加任何
        标志位，让离屏截图与逻辑分辨率一一对应。
        """
        if self.headless:
            return 0
        return pygame.RESIZABLE | pygame.SCALED

    def set_fullscreen(self, enabled: bool) -> None:
        """切换窗口 / 全屏显示。

        使用 SDL 的窗口级全屏切换，画面仍按逻辑分辨率缩放，宽高比不同时
        自动留黑边。headless 下只更新状态位，不做真实的窗口操作。
        """
        enabled = bool(enabled)
        if self.headless:
            self.fullscreen = enabled
            return
        if enabled != self.fullscreen:
            pygame.display.toggle_fullscreen()
        self.fullscreen = enabled

    def toggle_fullscreen(self) -> bool:
        """在窗口与全屏之间来回切换，返回切换后是否全屏。"""
        self.set_fullscreen(not self.fullscreen)
        return self.fullscreen

    # ------------------------------------------------------------------ 循环
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
            elif event.type == pygame.KEYDOWN and self.handle_key(event):
                continue
            else:
                self.screens.handle_event(event)

    def handle_key(self, event: pygame.event.Event) -> bool:
        """处理窗口级快捷键；返回 True 表示该按键已被消费。"""
        if event.key == pygame.K_F11:
            self.toggle_fullscreen()
            return True
        if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER) and event.mod & pygame.KMOD_ALT:
            self.toggle_fullscreen()
            return True
        if event.key == pygame.K_ESCAPE:
            # 全屏时先退回窗口，再按一次才退出程序
            if self.fullscreen:
                self.set_fullscreen(False)
            else:
                self.running = False
            return True
        return False

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