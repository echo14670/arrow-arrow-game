"""游戏流程测试。

对应作业要求里的 T01 - T06，另外覆盖撤销、计时与统计。
"""

from __future__ import annotations

import random
import unittest

from game.generator import Difficulty
from game.levels import Level
from game.session import ClickResult, Phase, Session, format_time
from game.setup import FIELD_ARROWS, FIELD_COLS, FIELD_ROWS
from game.solver import is_solvable, solve

# 测试用的极小关卡：一行一个朝右的箭头，点一下就通关
TINY = Level(name="迷你关", grid=(">.",), mistakes=1)
# 两个互不阻挡的箭头，用来测试撤销
PAIR = Level(name="成对关", grid=(">..", "<.."), mistakes=2)
# 边缘朝外的箭头：左上角朝上、左下角朝右
EDGE = Level(name="边缘关", grid=("^..", "...", ">.."), mistakes=3)


def blocked_cell(session: Session) -> tuple[int, int]:
    """找出当前棋盘上第一个被挡住的箭头。"""
    for row, col, _ in list(session.board.iter_arrows()):
        if not session.board.is_free(row, col):
            return row, col
    raise AssertionError("当前棋盘没有被挡住的箭头")


def free_cell(session: Session) -> tuple[int, int]:
    """找出当前棋盘上第一个可以飞出的箭头。"""
    for row, col, _ in list(session.board.iter_arrows()):
        if session.board.is_free(row, col):
            return row, col
    raise AssertionError("当前棋盘没有可以飞出的箭头")


class SessionTestBase(unittest.TestCase):
    def setUp(self) -> None:
        self.session = Session()
        self.session.start_game()


class StartAndClickTest(SessionTestBase):
    def test_start_game_enters_first_level(self) -> None:
        self.assertIs(self.session.phase, Phase.PLAYING)
        self.assertEqual(self.session.level_number, 1)
        self.assertEqual(self.session.mistakes_left, self.session.mistakes_total)

    def test_clicking_empty_cell_is_ignored(self) -> None:
        board = self.session.board
        empty = next(
            (row, col)
            for row in range(board.rows)
            for col in range(board.cols)
            if not board.has_arrow(row, col)
        )
        self.assertIs(self.session.click_cell(*empty), ClickResult.IGNORED)
        self.assertEqual(self.session.level_clicks, 0)

    def test_clicking_outside_the_board_is_ignored(self) -> None:
        self.assertIs(self.session.click_cell(-1, 0), ClickResult.IGNORED)
        self.assertIs(self.session.click_cell(99, 99), ClickResult.IGNORED)

    def test_buttons_are_disabled_before_start(self) -> None:
        fresh = Session()
        self.assertIs(fresh.phase, Phase.START)
        self.assertFalse(fresh.can_undo)
        self.assertIs(fresh.click_cell(0, 1), ClickResult.IGNORED)


class RequiredTestCases(SessionTestBase):
    """作业里要求记录的六个测试用例。"""

    def test_t01_clicking_free_arrow_removes_it(self) -> None:
        before = self.session.arrows_left
        row, col = free_cell(self.session)
        self.assertIs(self.session.click_cell(row, col), ClickResult.REMOVED)
        self.assertEqual(self.session.arrows_left, before - 1)
        self.assertFalse(self.session.board.has_arrow(row, col))
        self.assertEqual(self.session.mistakes_left, self.session.mistakes_total)

    def test_t02_clicking_blocked_arrow_only_costs_one_mistake(self) -> None:
        before = self.session.arrows_left
        mistakes = self.session.mistakes_left
        row, col = blocked_cell(self.session)
        self.assertIs(self.session.click_cell(row, col), ClickResult.BLOCKED)
        self.assertEqual(self.session.arrows_left, before, "被挡住的箭头不应该消失")
        self.assertTrue(self.session.board.has_arrow(row, col))
        self.assertEqual(self.session.mistakes_left, mistakes - 1)

    def test_t03_edge_arrow_facing_outwards_removes_without_error(self) -> None:
        session = Session([EDGE])
        session.start_game()
        self.assertIs(session.click_cell(0, 0), ClickResult.REMOVED)
        self.assertIs(session.click_cell(2, 0), ClickResult.REMOVED)
        self.assertIs(session.phase, Phase.LEVEL_CLEAR)

    def test_t04_clearing_every_arrow_clears_the_level(self) -> None:
        for row, col in solve(self.session.board):
            self.session.click_cell(row, col)
        self.assertEqual(self.session.arrows_left, 0)
        self.assertIs(self.session.phase, Phase.LEVEL_CLEAR)
        self.assertTrue(self.session.next_level())
        self.assertIs(self.session.phase, Phase.PLAYING)
        self.assertEqual(self.session.level_number, 2)

    def test_t05_running_out_of_mistakes_fails_the_level(self) -> None:
        self.session.mistakes_left = 1
        row, col = blocked_cell(self.session)
        self.session.click_cell(row, col)
        self.assertIs(self.session.phase, Phase.FAILED)
        self.assertEqual(self.session.mistakes_left, 0)
        # 失败后再点击不再生效
        self.assertIs(self.session.click_cell(row, col), ClickResult.IGNORED)

    def test_t06_restart_restores_layout_and_mistakes(self) -> None:
        initial = self.session.board.to_grid()
        total = self.session.mistakes_total
        self.session.click_cell(*blocked_cell(self.session))
        self.session.click_cell(*free_cell(self.session))
        self.session.tick(3.0)
        self.session.restart_level()
        self.assertEqual(self.session.board.to_grid(), initial)
        self.assertEqual(self.session.mistakes_left, total)
        self.assertEqual(self.session.level_time, 0.0)
        self.assertFalse(self.session.can_undo)
        self.assertIs(self.session.phase, Phase.PLAYING)


class LevelFlowTest(unittest.TestCase):
    def test_last_level_leads_to_all_clear(self) -> None:
        session = Session([TINY, TINY])
        session.start_game()
        session.click_cell(0, 0)
        self.assertIs(session.phase, Phase.LEVEL_CLEAR)
        self.assertTrue(session.next_level())
        session.click_cell(0, 0)
        self.assertIs(session.phase, Phase.LEVEL_CLEAR)
        self.assertFalse(session.next_level())
        self.assertIs(session.phase, Phase.ALL_CLEAR)

    def test_next_level_before_clearing_is_rejected(self) -> None:
        session = Session([TINY, TINY])
        session.start_game()
        self.assertFalse(session.next_level())
        self.assertEqual(session.level_number, 1)

    def test_back_to_menu_resets_progress(self) -> None:
        session = Session()
        session.start_game()
        session.click_cell(*free_cell(session))
        session.back_to_menu()
        self.assertIs(session.phase, Phase.START)
        self.assertEqual(session.level_number, 1)
        self.assertEqual(session.cleared_levels, 0)
        self.assertEqual(session.arrows_left, session.arrows_total)

    def test_session_requires_at_least_one_level(self) -> None:
        with self.assertRaises(ValueError):
            Session([])


class LevelSelectTest(unittest.TestCase):
    """选关功能：从主菜单挑一关直接开始。"""

    def test_open_level_select_from_start(self) -> None:
        session = Session()
        session.open_level_select()
        self.assertIs(session.phase, Phase.LEVEL_SELECT)
        self.assertIs(session.click_cell(0, 0), ClickResult.IGNORED)

    def test_open_level_select_is_ignored_while_playing(self) -> None:
        session = Session()
        session.start_game()
        session.open_level_select()
        self.assertIs(session.phase, Phase.PLAYING)

    def test_start_at_level_jumps_to_that_level(self) -> None:
        session = Session()
        session.start_at_level(3)
        self.assertIs(session.phase, Phase.PLAYING)
        self.assertEqual(session.level_number, 4)
        self.assertEqual(session.board.to_grid(), list(session.levels[3].grid))
        self.assertEqual(session.mistakes_left, session.levels[3].mistakes)

    def test_start_at_level_resets_progress(self) -> None:
        session = Session([TINY, TINY, TINY])
        session.start_game()
        session.click_cell(0, 0)  # 通关第 1 关
        session.tick(5.0)
        self.assertEqual(session.cleared_levels, 1)
        session.start_at_level(2)
        self.assertEqual(session.cleared_levels, 0)
        self.assertEqual(session.total_time, 0.0)
        self.assertEqual(session.total_clicks, 0)
        self.assertEqual(session.level_number, 3)
        self.assertEqual(session.level_time, 0.0)

    def test_start_game_is_level_one(self) -> None:
        session = Session()
        session.start_at_level(0)
        self.assertEqual(session.level_number, 1)
        session.back_to_menu()
        session.start_game()
        self.assertEqual(session.level_number, 1)

    def test_start_at_level_rejects_out_of_range(self) -> None:
        session = Session()
        with self.assertRaises(IndexError):
            session.start_at_level(session.level_count)
        with self.assertRaises(IndexError):
            session.start_at_level(-1)

    def test_back_to_menu_from_level_select(self) -> None:
        session = Session()
        session.open_level_select()
        session.back_to_menu()
        self.assertIs(session.phase, Phase.START)
        self.assertEqual(session.level_number, 1)


class UndoTest(unittest.TestCase):
    def setUp(self) -> None:
        self.session = Session([PAIR])
        self.session.start_game()

    def test_undo_restores_the_last_removed_arrow(self) -> None:
        initial = self.session.board.to_grid()
        self.session.click_cell(0, 0)
        self.assertEqual(self.session.arrows_left, 1)
        self.assertTrue(self.session.undo())
        self.assertEqual(self.session.board.to_grid(), initial)
        self.assertFalse(self.session.can_undo)

    def test_undo_costs_nothing(self) -> None:
        mistakes = self.session.mistakes_left
        self.session.click_cell(0, 0)
        self.session.undo()
        self.assertEqual(self.session.mistakes_left, mistakes)
        self.assertEqual(self.session.level_undos, 1)

    def test_undo_without_history_returns_false(self) -> None:
        self.assertFalse(self.session.undo())

    def test_undo_is_rejected_after_level_cleared(self) -> None:
        session = Session([TINY])
        session.start_game()
        session.click_cell(0, 0)
        self.assertIs(session.phase, Phase.LEVEL_CLEAR)
        self.assertFalse(session.undo())

    def test_restart_clears_undo_history(self) -> None:
        self.session.click_cell(0, 0)
        self.session.restart_level()
        self.assertFalse(self.session.can_undo)


class TimerAndSummaryTest(unittest.TestCase):
    def test_timer_runs_only_while_playing(self) -> None:
        session = Session([TINY, TINY])
        session.start_game()
        session.tick(1.5)
        self.assertAlmostEqual(session.level_time, 1.5)
        session.click_cell(0, 0)
        self.assertIs(session.phase, Phase.LEVEL_CLEAR)
        session.tick(2.0)
        self.assertAlmostEqual(session.level_time, 1.5)
        self.assertAlmostEqual(session.total_time, 1.5)

    def test_timer_ignores_negative_delta(self) -> None:
        session = Session()
        session.start_game()
        session.tick(-5.0)
        self.assertEqual(session.level_time, 0.0)

    def test_summary_reports_progress(self) -> None:
        session = Session([TINY, TINY])
        session.start_game()
        session.click_cell(0, 0)
        summary = session.summary()
        self.assertEqual(summary["cleared_levels"], 1)
        self.assertEqual(summary["level_count"], 2)
        self.assertEqual(summary["total_clicks"], 1)

    def test_format_time(self) -> None:
        self.assertEqual(format_time(0), "00:00")
        self.assertEqual(format_time(65.4), "01:05")
        self.assertEqual(format_time(600), "10:00")
        self.assertEqual(format_time(-3), "00:00")


class CustomLevelTest(unittest.TestCase):
    """自定义关卡：进设置面板、生成、开局、替换与重开。"""

    def setUp(self) -> None:
        self.session = Session()
        self.session.open_level_select()
        self.session.open_custom_setup()

    def test_open_custom_setup_from_level_select(self) -> None:
        self.assertIs(self.session.phase, Phase.CUSTOM_SETUP)

    def test_open_custom_setup_is_ignored_in_other_phases(self) -> None:
        session = Session()
        session.open_custom_setup()
        self.assertIs(session.phase, Phase.START)
        session.start_game()
        session.open_custom_setup()
        self.assertIs(session.phase, Phase.PLAYING)

    def test_close_custom_setup_returns_to_level_select(self) -> None:
        self.session.close_custom_setup()
        self.assertIs(self.session.phase, Phase.LEVEL_SELECT)

    def test_close_custom_setup_is_ignored_elsewhere(self) -> None:
        session = Session()
        session.close_custom_setup()
        self.assertIs(session.phase, Phase.START)

    def test_there_is_no_custom_level_before_generating(self) -> None:
        self.assertFalse(self.session.has_custom_level)
        self.assertEqual(self.session.custom_level_index, -1)
        self.assertEqual(self.session.level_count, self.session.builtin_level_count)

    def test_generate_starts_a_playable_custom_level(self) -> None:
        index = self.session.start_generated_custom_level(random.Random(2026))
        self.assertEqual(index, self.session.builtin_level_count)
        self.assertIs(self.session.phase, Phase.PLAYING)
        self.assertTrue(self.session.is_custom_level)
        self.assertEqual(self.session.level_number, self.session.level_count)
        self.assertEqual(self.session.board.arrow_count, self.session.custom_setup.arrows)
        self.assertTrue(is_solvable(self.session.board))

    def test_generated_level_matches_the_form(self) -> None:
        setup = self.session.custom_setup
        setup.set_value(FIELD_ROWS, 3)
        setup.set_value(FIELD_COLS, 4)
        setup.set_value(FIELD_ARROWS, 6)
        setup.set_difficulty(Difficulty.HIGH)
        self.session.start_generated_custom_level(random.Random(11))
        level = self.session.level
        self.assertEqual((level.rows, level.cols), (3, 4))
        self.assertEqual(level.arrow_count, 6)
        self.assertEqual(level.mistakes, setup.mistake_budget)
        self.assertIn(Difficulty.HIGH.label, level.name)

    def test_generating_twice_replaces_the_same_slot(self) -> None:
        builtin = Session().level_count
        self.session.start_generated_custom_level(random.Random(1))
        first = self.session.level
        self.session.back_to_menu()
        self.session.open_level_select()
        self.session.open_custom_setup()
        index = self.session.start_generated_custom_level(random.Random(2))
        self.assertEqual(index, builtin)
        self.assertEqual(self.session.level_count, builtin + 1, "自定义关卡只占一个槽位")
        self.assertIsNot(self.session.level, first)
        self.assertIs(self.session.levels[builtin], self.session.level)

    def test_custom_level_appears_in_the_level_list(self) -> None:
        index = self.session.start_generated_custom_level(random.Random(3))
        self.assertEqual(self.session.levels[index].name, self.session.level.name)
        self.assertEqual(self.session.builtin_level_count, 6)

    def test_custom_level_can_be_cleared_and_is_the_last_one(self) -> None:
        setup = self.session.custom_setup
        setup.set_value(FIELD_ROWS, 3)
        setup.set_value(FIELD_COLS, 3)
        setup.set_value(FIELD_ARROWS, 4)
        self.session.start_generated_custom_level(random.Random(7))
        while self.session.phase is Phase.PLAYING:
            order = solve(self.session.board)
            self.assertIsNotNone(order)
            self.session.click_cell(*order[0])
        self.assertIs(self.session.phase, Phase.LEVEL_CLEAR)
        self.assertEqual(self.session.cleared_levels, 1)
        self.assertFalse(self.session.next_level(), "自定义关卡是最后一关，应该全通关")
        self.assertIs(self.session.phase, Phase.ALL_CLEAR)

    def test_restart_restores_the_custom_level(self) -> None:
        self.session.start_generated_custom_level(random.Random(5))
        initial = self.session.board.to_grid()
        mistakes = self.session.mistakes_left
        self.session.click_cell(*solve(self.session.board)[0])
        self.session.restart_level()
        self.assertEqual(self.session.board.to_grid(), initial)
        self.assertEqual(self.session.mistakes_left, mistakes)
        self.assertIs(self.session.phase, Phase.PLAYING)

    def test_undo_works_inside_a_custom_level(self) -> None:
        self.session.start_generated_custom_level(random.Random(8))
        before = self.session.board.to_grid()
        self.session.click_cell(*solve(self.session.board)[0])
        self.assertTrue(self.session.undo())
        self.assertEqual(self.session.board.to_grid(), before)

    def test_restart_is_ignored_on_the_setup_panel(self) -> None:
        self.session.restart_level()
        self.assertIs(self.session.phase, Phase.CUSTOM_SETUP)

    def test_builtin_count_keeps_the_original_levels(self) -> None:
        session = Session([TINY, TINY])
        self.assertEqual(session.builtin_level_count, 2)
        session.open_level_select()
        session.open_custom_setup()
        session.start_generated_custom_level(random.Random(1))
        self.assertEqual(session.level_count, 3)
        self.assertEqual(session.is_custom_level, True)
        session.start_at_level(0)
        self.assertEqual(session.is_custom_level, False)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()