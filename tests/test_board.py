"""棋盘与路径检测的单元测试。"""

from __future__ import annotations

import unittest

from game.board import Board
from game.direction import Direction


class BoardConstructionTest(unittest.TestCase):
    def test_parse_all_four_directions(self) -> None:
        board = Board.from_grid(["^v<>"])
        self.assertEqual(
            [board.at(0, col) for col in range(4)],
            [Direction.UP, Direction.DOWN, Direction.LEFT, Direction.RIGHT],
        )

    def test_empty_cells_have_no_arrow(self) -> None:
        board = Board.from_grid([".>."])
        self.assertIsNone(board.at(0, 0))
        self.assertTrue(board.has_arrow(0, 1))
        self.assertFalse(board.has_arrow(0, 2))

    def test_arrow_count_and_iteration(self) -> None:
        board = Board.from_grid([".>v", "<.."])
        self.assertEqual(board.arrow_count, 3)
        self.assertEqual(
            [(row, col) for row, col, _ in board.iter_arrows()], [(0, 1), (0, 2), (1, 0)]
        )

    def test_round_trip_to_grid(self) -> None:
        grid = [".>v", "<.."]
        self.assertEqual(Board.from_grid(grid).to_grid(), grid)

    def test_rejects_ragged_grid(self) -> None:
        with self.assertRaises(ValueError):
            Board.from_grid([">>", ">"])

    def test_rejects_unknown_character(self) -> None:
        with self.assertRaises(ValueError):
            Board.from_grid([">x"])

    def test_rejects_empty_grid(self) -> None:
        with self.assertRaises(ValueError):
            Board.from_grid([])

    def test_remove_and_place(self) -> None:
        board = Board.from_grid([">.."])
        self.assertEqual(board.remove(0, 0), Direction.RIGHT)
        self.assertEqual(board.arrow_count, 0)
        board.place(0, 2, Direction.LEFT)
        self.assertEqual(board.at(0, 2), Direction.LEFT)

    def test_remove_empty_cell_raises(self) -> None:
        with self.assertRaises(ValueError):
            Board.from_grid(["."]).remove(0, 0)

    def test_out_of_range_access_raises(self) -> None:
        board = Board.from_grid([">."])
        with self.assertRaises(IndexError):
            board.at(1, 0)
        self.assertFalse(board.has_arrow(-1, 0))


class PathDetectionTest(unittest.TestCase):
    def test_path_clear_to_the_edge(self) -> None:
        board = Board.from_grid([">..", "...", "..<"])
        self.assertTrue(board.is_free(0, 0))
        self.assertTrue(board.is_free(2, 2))

    def test_blocked_by_arrow_directly_ahead(self) -> None:
        board = Board.from_grid([">v<"])
        self.assertFalse(board.is_free(0, 0))
        self.assertFalse(board.is_free(0, 2))

    def test_blocked_even_with_empty_cells_between(self) -> None:
        board = Board.from_grid([">..v"])
        self.assertFalse(board.is_free(0, 0))

    def test_blocking_only_counts_same_row_or_column(self) -> None:
        board = Board.from_grid([">..", ".v.", "..."])
        self.assertTrue(board.is_free(0, 0))

    def test_all_four_directions_blocked(self) -> None:
        """四种方向都要能在紧邻位置被挡住，且拿掉阻挡后恢复畅通。"""
        for direction in Direction:
            with self.subTest(direction=direction):
                d_row, d_col = direction.delta
                board = Board.empty(3, 3)
                board.place(1, 1, direction)
                self.assertTrue(board.is_free(1, 1), "空棋盘上应该是畅通的")
                board.place(1 + d_row, 1 + d_col, Direction.UP)
                self.assertFalse(board.is_free(1, 1), "紧邻方向上有箭头应被挡住")
                board.remove(1 + d_row, 1 + d_col)
                self.assertTrue(board.is_free(1, 1))

    def test_direction_characters_match_grid_notation(self) -> None:
        self.assertEqual(Direction.UP.char, "^")
        self.assertEqual(Direction.DOWN.char, "v")
        self.assertEqual(Direction.LEFT.char, "<")
        self.assertEqual(Direction.RIGHT.char, ">")

    def test_arrow_at_edge_facing_outwards_is_free(self) -> None:
        grid = (
            "^..",
            "...",
            ">..",
        )
        board = Board.from_grid(grid)
        self.assertTrue(board.is_free(0, 0))
        self.assertTrue(board.is_free(2, 0))

    def test_negative_index_wraparound_regression(self) -> None:
        """回归用例：向上检测不能因为负索引绕到棋盘底部。

        如果实现里写成 ``grid[row - 1][col]`` 而不判断边界，Python 的负
        索引会让 (0, 0) 去查 (2, 0)，把棋盘底部的箭头误当成阻挡。
        """
        board = Board.from_grid(["^..", "...", "^.."])
        self.assertTrue(board.is_free(0, 0))
        self.assertFalse(board.is_free(2, 0))

    def test_empty_cell_is_never_free(self) -> None:
        board = Board.from_grid(["..."])
        self.assertFalse(board.is_free(0, 0))

    def test_copy_is_independent(self) -> None:
        board = Board.from_grid([">.v"])
        clone = board.copy()
        clone.remove(0, 0)
        self.assertEqual(board.arrow_count, 2)
        self.assertEqual(clone.arrow_count, 1)