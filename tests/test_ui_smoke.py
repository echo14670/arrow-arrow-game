"""界面层冒烟测试。

在 SDL 的 dummy 视频驱动下模拟真实鼠标事件，验证「事件 → Session 状态」
的接线正确，并确保各个界面阶段都能正常绘制。
"""

from __future__ import annotations

import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

from game.app import Game  # noqa: E402
from game.session import ClickResult, Phase  # noqa: E402
from game.solver import solve  # noqa: E402
from game.ui import layout  # noqa: E402


class UiSmokeTest(unittest.TestCase):
    def setUp(self) -> None:
        self.game = Game(headless=True)
        self.screen = self.game.screens.game_screen

    def tearDown(self) -> None:
        pygame.quit()

    # ---------- 工具 ----------

    def click(self, pos: tuple[int, int]) -> None:
        pygame.event.post(
            pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"pos": pos, "button": 1})
        )
        self.game.handle_events()

    def cell_center(self, row: int, col: int) -> tuple[int, int]:
        board = self.game.session.board
        rect = layout.board_rect(board.rows, board.cols)
        return layout.cell_rect(rect, row, col).center

    def start_game(self) -> None:
        self.click(self.game.screens.start_screen.btn_start.rect.center)

    def find(self, want_free: bool) -> tuple[int, int]:
        for row, col, _ in list(self.game.session.board.iter_arrows()):
            if self.game.session.board.is_free(row, col) is want_free:
                return row, col
        raise AssertionError("找不到符合条件的箭头")

    # ---------- 用例 ----------

    def test_start_button_starts_the_game(self) -> None:
        self.start_game()
        self.assertIs(self.game.session.phase, Phase.PLAYING)

    def test_clicking_a_free_cell_removes_the_arrow(self) -> None:
        self.start_game()
        session = self.game.session
        before = session.arrows_left
        result = self.screen.click_cell(*self.find(True))
        self.assertIs(result, ClickResult.REMOVED)
        self.assertEqual(session.arrows_left, before - 1)
        self.assertTrue(self.screen.animations.busy)

    def test_clicking_a_blocked_cell_costs_a_mistake(self) -> None:
        self.start_game()
        session = self.game.session
        mistakes = session.mistakes_left
        result = self.screen.click_cell(*self.find(False))
        self.assertIs(result, ClickResult.BLOCKED)
        self.assertEqual(session.mistakes_left, mistakes - 1)

    def test_board_click_goes_through_the_mouse_event(self) -> None:
        self.start_game()
        session = self.game.session
        before = session.arrows_left
        self.click(self.cell_center(*self.find(True)))
        self.assertEqual(session.arrows_left, before - 1)

    def test_clicks_are_ignored_while_an_animation_is_playing(self) -> None:
        self.start_game()
        session = self.game.session
        self.screen.click_cell(*self.find(True))
        before = session.arrows_left
        self.click(self.cell_center(*self.find(True)))
        self.assertEqual(session.arrows_left, before, "动画期间不应该再结算一次点击")

    def test_restart_button_restores_the_level(self) -> None:
        self.start_game()
        session = self.game.session
        initial = session.board.to_grid()
        self.screen.click_cell(*self.find(True))
        self.screen.animations.clear()
        self.click(self.screen.btn_restart.rect.center)
        self.assertEqual(session.board.to_grid(), initial)
        self.assertIs(session.phase, Phase.PLAYING)

    def test_level_select_button_opens_the_panel(self) -> None:
        start = self.game.screens.start_screen
        self.click(start.btn_level_select.rect.center)
        self.assertIs(self.game.session.phase, Phase.LEVEL_SELECT)
        self.game.draw()  # 选关面板必须能正常绘制

    def test_clicking_a_level_row_starts_that_level(self) -> None:
        start = self.game.screens.start_screen
        self.click(start.btn_level_select.rect.center)
        self.click(start.level_row_rect(3).center)
        self.assertIs(self.game.session.phase, Phase.PLAYING)
        self.assertEqual(self.game.session.level_number, 4)

    def test_level_select_back_button_returns_to_menu(self) -> None:
        start = self.game.screens.start_screen
        self.click(start.btn_level_select.rect.center)
        self.click(start.btn_back.rect.center)
        self.assertIs(self.game.session.phase, Phase.START)

    def test_number_key_starts_a_level(self) -> None:
        self.game.session.open_level_select()
        pygame.event.post(
            pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_5, "mod": 0, "unicode": "5"})
        )
        self.game.handle_events()
        self.assertIs(self.game.session.phase, Phase.PLAYING)
        self.assertEqual(self.game.session.level_number, 5)

    def test_survives_restarting_pygame(self) -> None:
        """pygame 重新初始化后仍然能正常绘制。

        字体与箭头贴图是带缓存的，pygame.quit() 之后再 init，缓存里的对象
        会引用已经释放的底层资源；如果不丢弃缓存，第二次绘制会让进程直接
        崩溃（访问违例 0xC0000005）。
        """
        self.game.draw()
        pygame.quit()
        second = Game(headless=True)
        second.draw()
        second.session.start_game()
        second.draw()

    def test_every_phase_can_be_rendered(self) -> None:
        surfaces = []

        def snapshot() -> None:
            self.game.draw()
            surfaces.append(self.game.screen.get_at((10, 10)))

        snapshot()  # 开始界面
        self.start_game()
        snapshot()  # 游戏界面
        while self.game.session.phase is Phase.PLAYING:
            self.game.session.click_cell(*solve(self.game.session.board)[0])
        self.screen.animations.clear()
        snapshot()  # 过关界面
        self.game.session.restart_level()
        self.game.session.mistakes_left = 1
        self.screen.click_cell(*self.find(False))
        self.screen.animations.clear()
        snapshot()  # 失败界面
        self.game.session.restart_level()
        while self.game.session.phase is not Phase.ALL_CLEAR:
            if self.game.session.phase is Phase.PLAYING:
                while self.game.session.phase is Phase.PLAYING:
                    self.game.session.click_cell(*solve(self.game.session.board)[0])
            else:
                self.game.session.next_level()
        self.screen.animations.clear()
        snapshot()  # 全部通关界面
        self.assertEqual(len(surfaces), 5)