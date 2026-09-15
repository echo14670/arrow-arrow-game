"""游戏流程测试。

对应作业要求里的 T01 - T06，另外覆盖撤销、计时与统计。
"""

from __future__ import annotations

import unittest

from game.levels import Level
from game.session import ClickResult, Phase, Session, format_time
from game.solver import solve

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


if __name__ == "__main__":  # pragma: no cover
    unittest.main()