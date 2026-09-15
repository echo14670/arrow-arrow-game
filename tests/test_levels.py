"""关卡数据测试：布局合法、数量正确、每一关都能通关。"""

from __future__ import annotations

import unittest

from game.board import Board
from game.levels import LEVELS
from game.solver import describe, is_solvable, solve


class LevelDataTest(unittest.TestCase):
    def test_has_at_least_three_levels(self) -> None:
        self.assertGreaterEqual(len(LEVELS), 3)

    def test_level_names_and_mistakes(self) -> None:
        for index, level in enumerate(LEVELS, start=1):
            with self.subTest(level=index):
                self.assertTrue(level.name.strip())
                self.assertGreater(level.mistakes, 0)

    def test_boards_are_rectangular_and_use_known_characters(self) -> None:
        for level in LEVELS:
            with self.subTest(level=level.name):
                self.assertGreater(level.rows, 0)
                widths = {len(line) for line in level.grid}
                self.assertEqual(len(widths), 1)
                Board.from_grid(level.grid)

    def test_every_level_has_arrows(self) -> None:
        for level in LEVELS:
            with self.subTest(level=level.name):
                self.assertGreaterEqual(level.arrow_count, 3)

    def test_every_level_is_solvable(self) -> None:
        for level in LEVELS:
            with self.subTest(level=level.name):
                board = Board.from_grid(level.grid)
                self.assertTrue(is_solvable(board), f"{level.name} 无法通关")

    def test_solution_clears_the_whole_board(self) -> None:
        for level in LEVELS:
            with self.subTest(level=level.name):
                board = Board.from_grid(level.grid)
                order = solve(board)
                self.assertIsNotNone(order)
                self.assertEqual(len(order), level.arrow_count)
                for row, col in order:
                    self.assertTrue(board.is_free(row, col))
                    board.remove(row, col)
                self.assertEqual(board.arrow_count, 0)

    def test_levels_are_not_trivial(self) -> None:
        """每一关开局都至少有一个箭头是被挡住的，避免关卡一眼看穿。"""
        for level in LEVELS:
            with self.subTest(level=level.name):
                stats = describe(Board.from_grid(level.grid))
                self.assertGreater(stats["blocked_at_start"], 0)

    def test_difficulty_grows_with_level_size(self) -> None:
        sizes = [level.rows for level in LEVELS]
        self.assertEqual(sizes, sorted(sizes))