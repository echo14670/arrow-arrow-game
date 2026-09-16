"""自定义关卡表单测试：范围夹紧、上限联动、难度选择与生成。"""

from __future__ import annotations

import random
import unittest

from game import generator
from game.board import Board
from game.generator import Difficulty
from game.setup import FIELD_ARROWS, FIELD_COLS, FIELD_ROWS, FIELDS, CustomSetup
from game.solver import is_solvable


class DefaultsTest(unittest.TestCase):
    def test_defaults_are_inside_the_allowed_range(self) -> None:
        setup = CustomSetup()
        self.assertEqual((setup.rows, setup.cols), (5, 5))
        self.assertEqual(setup.arrows, 8)
        self.assertIs(setup.difficulty, Difficulty.MEDIUM)
        self.assertEqual(setup.focus, FIELD_ROWS)

    def test_out_of_range_init_is_clamped(self) -> None:
        setup = CustomSetup(rows=99, cols=0, arrows=1000, difficulty=Difficulty.HIGH)
        self.assertEqual(setup.rows, generator.MAX_SIZE)
        self.assertEqual(setup.cols, generator.MIN_SIZE)
        self.assertEqual(setup.arrows, generator.MAX_SIZE * generator.MIN_SIZE)
        self.assertIs(setup.difficulty, Difficulty.HIGH)


class LimitsTest(unittest.TestCase):
    def test_max_arrows_follows_the_board_size(self) -> None:
        setup = CustomSetup(rows=3, cols=4, arrows=5)
        self.assertEqual(setup.max_arrows, 12)
        setup.set_value(FIELD_ROWS, 6)
        setup.set_value(FIELD_COLS, 6)
        self.assertEqual(setup.max_arrows, 36)

    def test_limits_reports_both_bounds(self) -> None:
        setup = CustomSetup(rows=3, cols=4, arrows=5)
        self.assertEqual(setup.limits(FIELD_ROWS), (generator.MIN_SIZE, generator.MAX_SIZE))
        self.assertEqual(setup.limits(FIELD_ARROWS), (1, 12))

    def test_shrinking_the_board_clamps_the_arrow_count(self) -> None:
        setup = CustomSetup(rows=6, cols=6, arrows=36)
        self.assertTrue(setup.set_value(FIELD_ROWS, 3))
        self.assertEqual(setup.rows, 3)
        self.assertEqual(setup.arrows, 18, "棋盘变小之后箭头数量要跟着夹紧")

    def test_shrinking_the_board_can_leave_the_arrow_count_alone(self) -> None:
        setup = CustomSetup(rows=6, cols=6, arrows=4)
        setup.set_value(FIELD_ROWS, 2)
        self.assertEqual(setup.arrows, 4)

    def test_size_cannot_shrink_below_two(self) -> None:
        setup = CustomSetup(rows=2, cols=2, arrows=1)
        setup.adjust(-1, FIELD_ROWS)
        self.assertEqual(setup.rows, generator.MIN_SIZE)
        setup.adjust(-5, FIELD_COLS)
        self.assertEqual(setup.cols, generator.MIN_SIZE)

    def test_size_cannot_grow_past_the_maximum(self) -> None:
        setup = CustomSetup(rows=6, cols=6, arrows=1)
        self.assertFalse(setup.adjust(1, FIELD_ROWS), "已经到上限就不再变化")
        self.assertEqual(setup.rows, generator.MAX_SIZE)

    def test_arrows_stay_between_one_and_the_cell_count(self) -> None:
        setup = CustomSetup(rows=2, cols=3, arrows=1)
        setup.adjust(99, FIELD_ARROWS)
        self.assertEqual(setup.arrows, 6)
        setup.adjust(-99, FIELD_ARROWS)
        self.assertEqual(setup.arrows, 1)

    def test_fill_arrows_jumps_between_the_limits(self) -> None:
        setup = CustomSetup(rows=4, cols=4, arrows=2)
        self.assertTrue(setup.fill_arrows(True))
        self.assertEqual(setup.arrows, 16)
        self.assertFalse(setup.fill_arrows(True))
        self.assertTrue(setup.fill_arrows(False))
        self.assertEqual(setup.arrows, 1)


class FocusTest(unittest.TestCase):
    def test_focus_cycles_through_every_field(self) -> None:
        setup = CustomSetup()
        seen = {setup.focus}
        for _ in range(len(FIELDS) - 1):
            seen.add(setup.move_focus(1))
        self.assertEqual(seen, set(FIELDS))
        self.assertEqual(setup.move_focus(1), FIELD_ROWS)

    def test_adjust_uses_the_focused_field(self) -> None:
        setup = CustomSetup()
        setup.focus_on(FIELD_COLS)
        setup.adjust(1)
        self.assertEqual(setup.cols, 6)

    def test_unknown_field_is_rejected(self) -> None:
        setup = CustomSetup()
        with self.assertRaises(ValueError):
            setup.set_value("size", 3)
        with self.assertRaises(ValueError):
            setup.focus_on("nope")
        with self.assertRaises(ValueError):
            setup.value("nope")


class DifficultyTest(unittest.TestCase):
    def test_set_difficulty_reports_changes(self) -> None:
        setup = CustomSetup()
        self.assertFalse(setup.set_difficulty(Difficulty.MEDIUM))
        self.assertTrue(setup.set_difficulty(Difficulty.HIGH))
        self.assertIs(setup.difficulty, Difficulty.HIGH)

    def test_cycle_walks_through_the_three_levels(self) -> None:
        setup = CustomSetup()
        self.assertIs(setup.cycle_difficulty(1), Difficulty.HIGH)
        self.assertIs(setup.cycle_difficulty(1), Difficulty.LOW)
        self.assertIs(setup.cycle_difficulty(-1), Difficulty.HIGH)

    def test_mistake_budget_follows_the_difficulty(self) -> None:
        setup = CustomSetup(rows=6, cols=6, arrows=20)
        setup.set_difficulty(Difficulty.LOW)
        low = setup.mistake_budget
        setup.set_difficulty(Difficulty.HIGH)
        self.assertLess(setup.mistake_budget, low)
        self.assertEqual(setup.mistake_budget, generator.mistake_budget(20, Difficulty.HIGH))


class BuildTest(unittest.TestCase):
    def test_build_uses_the_current_settings(self) -> None:
        setup = CustomSetup(rows=4, cols=5, arrows=7, difficulty=Difficulty.HIGH)
        level = setup.build(random.Random(9))
        self.assertEqual((level.rows, level.cols), (4, 5))
        self.assertEqual(level.arrow_count, 7)
        self.assertEqual(level.mistakes, generator.mistake_budget(7, Difficulty.HIGH))
        self.assertTrue(is_solvable(Board.from_grid(level.grid)))

    def test_build_after_shrinking_the_board_still_matches(self) -> None:
        setup = CustomSetup(rows=6, cols=6, arrows=36)
        setup.set_value(FIELD_ROWS, 3)
        setup.set_value(FIELD_COLS, 3)
        level = setup.build(random.Random(2))
        self.assertEqual((level.rows, level.cols), (3, 3))
        self.assertEqual(level.arrow_count, setup.arrows)
        self.assertTrue(is_solvable(Board.from_grid(level.grid)))

    def test_summary_mentions_every_field(self) -> None:
        setup = CustomSetup(rows=3, cols=4, arrows=5, difficulty=Difficulty.LOW)
        text = setup.summary()
        self.assertIn("3 × 4", text)
        self.assertIn("5", text)
        self.assertIn(Difficulty.LOW.label, text)
        self.assertIn(str(setup.mistake_budget), text)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()