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
from game.generator import Difficulty  # noqa: E402
from game.session import ClickResult, Phase  # noqa: E402
from game.setup import FIELD_ARROWS, FIELD_COLS, FIELD_ROWS  # noqa: E402
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

    def press(self, key: int) -> None:
        pygame.event.post(
            pygame.event.Event(pygame.KEYDOWN, {"key": key, "mod": 0, "unicode": ""})
        )
        self.game.handle_events()

    def open_custom_panel(self) -> None:
        """从主菜单依次进入选关界面与「自定义关卡」面板。"""
        start = self.game.screens.start_screen
        self.click(start.btn_level_select.rect.center)
        start.active_buttons()  # 让「自定义关卡」按钮先按关卡数量定位
        self.click(start.btn_custom.rect.center)

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

    # ---------- 自定义关卡 ----------

    def test_custom_button_opens_the_setup_panel(self) -> None:
        self.open_custom_panel()
        self.assertIs(self.game.session.phase, Phase.CUSTOM_SETUP)
        self.game.draw()

    def test_stepper_buttons_change_the_board_size(self) -> None:
        self.open_custom_panel()
        start = self.game.screens.start_screen
        setup = self.game.session.custom_setup
        rows = setup.rows
        self.click(start.btn_plus[FIELD_ROWS].rect.center)
        self.assertEqual(setup.rows, rows + 1)
        self.click(start.btn_minus[FIELD_ROWS].rect.center)
        self.assertEqual(setup.rows, rows)

    def test_plus_button_is_disabled_at_the_limit(self) -> None:
        self.open_custom_panel()
        start = self.game.screens.start_screen
        setup = self.game.session.custom_setup
        setup.set_value(FIELD_ROWS, setup.max_size)
        self.click(start.btn_plus[FIELD_ROWS].rect.center)
        self.assertEqual(setup.rows, setup.max_size, "到了上限，加号就不该再生效")

    def test_shrinking_the_board_clamps_the_arrows_in_the_panel(self) -> None:
        self.open_custom_panel()
        start = self.game.screens.start_screen
        setup = self.game.session.custom_setup
        setup.set_value(FIELD_ROWS, 6)
        setup.set_value(FIELD_COLS, 6)
        setup.set_value(FIELD_ARROWS, 36)
        self.click(start.btn_minus[FIELD_ROWS].rect.center)
        self.assertEqual(setup.rows, 5)
        self.assertEqual(setup.arrows, 30, "棋盘变成 5×6 之后箭头数量要跟着夹紧")
        self.game.draw()

    def test_fill_button_and_difficulty_buttons(self) -> None:
        self.open_custom_panel()
        start = self.game.screens.start_screen
        setup = self.game.session.custom_setup
        setup.set_value(FIELD_ROWS, 4)
        setup.set_value(FIELD_COLS, 4)
        self.click(start.btn_fill_arrows.rect.center)
        self.assertEqual(setup.arrows, 16)
        self.click(start.difficulty_buttons[Difficulty.HIGH].rect.center)
        self.assertIs(setup.difficulty, Difficulty.HIGH)
        self.click(start.difficulty_buttons[Difficulty.LOW].rect.center)
        self.assertIs(setup.difficulty, Difficulty.LOW)
        self.game.draw()

    def test_generate_button_starts_a_custom_level(self) -> None:
        self.open_custom_panel()
        start = self.game.screens.start_screen
        setup = self.game.session.custom_setup
        setup.set_value(FIELD_ROWS, 3)
        setup.set_value(FIELD_COLS, 3)
        setup.set_value(FIELD_ARROWS, 4)
        builtin = self.game.session.builtin_level_count
        self.click(start.btn_generate.rect.center)
        session = self.game.session
        self.assertIs(session.phase, Phase.PLAYING)
        self.assertEqual(session.level_count, builtin + 1)
        self.assertEqual(session.level_number, builtin + 1)
        self.assertEqual(session.board.arrow_count, 4)
        self.game.draw()  # 自定义关卡的棋盘也要能画出来

    def test_back_button_returns_to_level_select(self) -> None:
        self.open_custom_panel()
        start = self.game.screens.start_screen
        self.click(start.btn_custom_back.rect.center)
        self.assertIs(self.game.session.phase, Phase.LEVEL_SELECT)
        self.game.draw()

    def test_c_key_opens_the_custom_panel(self) -> None:
        self.click(self.game.screens.start_screen.btn_level_select.rect.center)
        self.press(pygame.K_c)
        self.assertIs(self.game.session.phase, Phase.CUSTOM_SETUP)

    def test_backspace_closes_the_custom_panel(self) -> None:
        self.open_custom_panel()
        self.press(pygame.K_BACKSPACE)
        self.assertIs(self.game.session.phase, Phase.LEVEL_SELECT)

    def test_custom_panel_keyboard_controls(self) -> None:
        self.open_custom_panel()
        setup = self.game.session.custom_setup
        self.press(pygame.K_3)
        self.assertIs(setup.difficulty, Difficulty.HIGH)
        self.press(pygame.K_DOWN)
        self.assertEqual(setup.focus, FIELD_COLS)
        before = setup.cols
        self.press(pygame.K_RIGHT)
        self.assertEqual(setup.cols, before + 1)
        self.press(pygame.K_LEFT)
        self.assertEqual(setup.cols, before)
        self.press(pygame.K_f)
        self.assertEqual(setup.arrows, setup.max_arrows)
        self.press(pygame.K_RETURN)
        self.assertIs(self.game.session.phase, Phase.PLAYING)

    def test_generated_level_can_be_replayed_from_the_level_list(self) -> None:
        self.open_custom_panel()
        start = self.game.screens.start_screen
        self.game.session.custom_setup.set_value(FIELD_ARROWS, 5)
        self.click(start.btn_generate.rect.center)
        index = self.game.session.custom_level_index
        self.game.session.back_to_menu()
        self.click(start.btn_level_select.rect.center)
        self.click(start.level_row_rect(index).center)
        self.assertIs(self.game.session.phase, Phase.PLAYING)
        self.assertEqual(self.game.session.level_number, index + 1)

    # ---------- 返回主菜单 ----------

    def test_every_level_screen_has_a_back_to_menu_button(self) -> None:
        """内置关卡与自定义关卡的界面都带「返回主菜单」。"""
        session = self.game.session
        for index in range(session.level_count):
            with self.subTest(level=index + 1):
                session.start_at_level(index)
                self.assertIn(self.screen.btn_bottom_menu, self.screen.active_buttons())
        self.open_custom_panel()
        start = self.game.screens.start_screen
        self.click(start.btn_generate.rect.center)
        self.assertIn(self.screen.btn_bottom_menu, self.screen.active_buttons())

    def test_bottom_menu_button_aborts_the_level(self) -> None:
        self.start_game()
        session = self.game.session
        session.click_cell(*self.find(True))
        self.screen.animations.clear()
        self.assertNotEqual(session.board.to_grid(), list(session.levels[0].grid))
        self.click(self.screen.btn_bottom_menu.rect.center)
        self.assertIs(session.phase, Phase.START)
        self.assertEqual(session.level_number, 1)
        self.assertEqual(session.cleared_levels, 0)
        self.assertEqual(session.total_clicks, 0)
        self.assertEqual(session.arrows_left, session.arrows_total)
        self.assertEqual(session.board.to_grid(), list(session.levels[0].grid))
        self.game.draw()  # 回到主菜单之后要能正常绘制

    def test_bottom_menu_button_aborts_a_custom_level(self) -> None:
        self.open_custom_panel()
        start = self.game.screens.start_screen
        self.game.session.custom_setup.set_value(FIELD_ARROWS, 5)
        self.click(start.btn_generate.rect.center)
        session = self.game.session
        self.assertTrue(session.is_custom_level)
        self.click(self.screen.btn_bottom_menu.rect.center)
        self.assertIs(session.phase, Phase.START)
        self.assertEqual(session.level_number, 1)
        self.assertTrue(session.has_custom_level, "自定义关卡应该还留在选关列表里")

    def test_m_key_returns_to_the_menu(self) -> None:
        self.start_game()
        self.press(pygame.K_m)
        self.assertIs(self.game.session.phase, Phase.START)
        self.assertEqual(self.game.session.level_number, 1)

    def test_bottom_menu_is_locked_during_an_animation(self) -> None:
        """动画期间输入被锁定，返回主菜单也不例外。"""
        self.start_game()
        self.screen.click_cell(*self.find(True))
        self.assertTrue(self.screen.animations.busy)
        self.click(self.screen.btn_bottom_menu.rect.center)
        self.assertIs(self.game.session.phase, Phase.PLAYING)
        self.screen.animations.clear()
        self.click(self.screen.btn_bottom_menu.rect.center)
        self.assertIs(self.game.session.phase, Phase.START)

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
        self.click(self.game.screens.start_screen.btn_level_select.rect.center)
        snapshot()  # 选关界面（含自定义关卡入口）
        self.game.session.open_custom_setup()
        snapshot()  # 自定义关卡面板
        self.game.session.back_to_menu()
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
        self.assertEqual(len(surfaces), 7)