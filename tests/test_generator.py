"""关卡生成器测试：参数夹紧、数量上限、难度评分与「生成即保证有解」。"""

from __future__ import annotations

import random
import unittest

from game import generator
from game.board import Board
from game.generator import Difficulty
from game.solver import describe, is_solvable, solve

SIZES = tuple(
    (rows, cols)
    for rows in range(generator.MIN_SIZE, generator.MAX_SIZE + 1)
    for cols in range(generator.MIN_SIZE, generator.MAX_SIZE + 1)
)
# 每个大小里挑几个有代表性的箭头数量，避免用例跑得太慢
DENSITIES = (1, 4, 8, 15, 36)


class ClampTest(unittest.TestCase):
    def test_size_is_clamped_to_the_supported_range(self) -> None:
        self.assertEqual(generator.clamp_size(-3), generator.MIN_SIZE)
        self.assertEqual(generator.clamp_size(0), generator.MIN_SIZE)
        self.assertEqual(generator.clamp_size(4), 4)
        self.assertEqual(generator.clamp_size(99), generator.MAX_SIZE)
        self.assertEqual(generator.clamp_size(generator.MAX_SIZE), generator.MAX_SIZE)

    def test_bad_size_input_falls_back_to_the_lower_bound(self) -> None:
        self.assertEqual(generator.clamp_size(None), generator.MIN_SIZE)
        self.assertEqual(generator.clamp_size("abc"), generator.MIN_SIZE)
        self.assertEqual(generator.clamp_size(2.7), generator.MIN_SIZE)

    def test_max_arrows_is_every_cell_of_the_board(self) -> None:
        for rows, cols in SIZES:
            with self.subTest(size=(rows, cols)):
                self.assertEqual(generator.max_arrows(rows, cols), rows * cols)

    def test_arrow_count_is_clamped_between_one_and_the_maximum(self) -> None:
        self.assertEqual(generator.clamp_arrows(0, 4, 4), 1)
        self.assertEqual(generator.clamp_arrows(-5, 4, 4), 1)
        self.assertEqual(generator.clamp_arrows(16, 4, 4), 16)
        self.assertEqual(generator.clamp_arrows(99, 4, 4), 16)
        self.assertEqual(generator.clamp_arrows(None, 4, 4), 1)

    def test_mistake_budget_stays_inside_the_configured_range(self) -> None:
        for arrows in (1, 4, 12, 24, 36):
            for difficulty in Difficulty:
                with self.subTest(arrows=arrows, difficulty=difficulty.value):
                    budget = generator.mistake_budget(arrows, difficulty)
                    self.assertGreaterEqual(budget, generator.MIN_MISTAKES)
                    self.assertLessEqual(budget, generator.MAX_MISTAKES)

    def test_harder_difficulty_allows_fewer_mistakes(self) -> None:
        for arrows in (8, 12, 20):
            with self.subTest(arrows=arrows):
                self.assertLessEqual(
                    generator.mistake_budget(arrows, Difficulty.HIGH),
                    generator.mistake_budget(arrows, Difficulty.LOW),
                )


class ScoreTest(unittest.TestCase):
    """评分就是难度排序用的 best_layout 分数。"""

    def test_unsolvable_board_scores_negative(self) -> None:
        board = Board.from_grid((">><",))  # 三个箭头互相挡住，谁也飞不出去
        self.assertFalse(is_solvable(board))
        self.assertEqual(generator.score(board), -1.0)

    def test_solvable_board_scores_at_least_zero(self) -> None:
        board = Board.from_grid((">.",))
        self.assertGreaterEqual(generator.score(board), 0.0)

    def test_score_grows_with_the_blocked_ratio(self) -> None:
        easy = Board.from_grid((">.", "<."))
        hard = Board.from_grid((">v", "<."))
        self.assertGreater(generator.score(hard), generator.score(easy))


class GenerateTest(unittest.TestCase):
    def test_every_size_and_density_is_solvable(self) -> None:
        """2×2 到 6×6、每个箭头数量都必须生成出「数量正确且可解」的棋盘。"""
        rng = random.Random(20260916)
        for rows, cols in SIZES:
            for arrows in range(1, rows * cols + 1):
                with self.subTest(size=(rows, cols), arrows=arrows):
                    board = generator.generate(
                        rows, cols, arrows, Difficulty.MEDIUM, rng, candidates=6
                    )
                    self.assertEqual((board.rows, board.cols), (rows, cols))
                    self.assertEqual(board.arrow_count, arrows)
                    self.assertEqual(len(board.to_grid()[0]), cols)
                    order = solve(board)
                    self.assertIsNotNone(order, "生成的关卡必须可解")
                    self.assertEqual(len(order), arrows)

    def test_generated_arrow_count_is_clamped(self) -> None:
        rng = random.Random(4)
        board = generator.generate(3, 3, 99, Difficulty.MEDIUM, rng, candidates=4)
        self.assertEqual(board.arrow_count, 9)
        board = generator.generate(3, 3, -5, Difficulty.MEDIUM, rng, candidates=4)
        self.assertEqual(board.arrow_count, 1)

    def test_difficulty_picks_from_the_same_candidate_pool(self) -> None:
        """同一批候选里，难度越高分数越高。"""
        for rows, cols in ((5, 5), (6, 6), (4, 4)):
            for arrows in (6, 12, 20, 36):
                if arrows > rows * cols:
                    continue
                with self.subTest(size=(rows, cols), arrows=arrows):
                    scores = [
                        generator.score(
                            generator.generate(
                                rows, cols, arrows, difficulty, random.Random(7)
                            )
                        )
                        for difficulty in (Difficulty.LOW, Difficulty.MEDIUM, Difficulty.HIGH)
                    ]
                    self.assertLessEqual(scores[0], scores[1])
                    self.assertLessEqual(scores[1], scores[2])

    def test_generation_is_reproducible_with_the_same_seed(self) -> None:
        first = generator.generate(5, 5, 10, Difficulty.HIGH, random.Random(2026))
        second = generator.generate(5, 5, 10, Difficulty.HIGH, random.Random(2026))
        other = generator.generate(5, 5, 10, Difficulty.HIGH, random.Random(2027))
        self.assertEqual(first.to_grid(), second.to_grid())
        self.assertNotEqual(first.to_grid(), other.to_grid())


class OnionLayoutTest(unittest.TestCase):
    """洋葱式摆放是「任意箭头数量都能生成」的兜底方案。"""

    def test_onion_layout_handles_every_density(self) -> None:
        rng = random.Random(5)
        for rows, cols in ((2, 2), (3, 5), (6, 6)):
            for arrows in range(1, rows * cols + 1):
                with self.subTest(size=(rows, cols), arrows=arrows):
                    board = generator.onion_layout(rows, cols, arrows, rng)
                    self.assertEqual(board.arrow_count, arrows)
                    self.assertTrue(is_solvable(board))

    def test_random_layout_returns_none_when_it_cannot_fill_the_board(self) -> None:
        """单个格子塞不下两个箭头，随机摆放失败时要老实返回 None。"""
        self.assertIsNone(generator.random_layout(1, 1, 2, random.Random(1), attempts=2))


class BuildLevelTest(unittest.TestCase):
    def test_build_level_matches_the_requested_settings(self) -> None:
        level = generator.build_level(6, 5, 12, Difficulty.HIGH, random.Random(3))
        self.assertEqual((level.rows, level.cols), (6, 5))
        self.assertEqual(level.arrow_count, 12)
        self.assertEqual(level.mistakes, generator.mistake_budget(12, Difficulty.HIGH))
        self.assertIn(Difficulty.HIGH.label, level.name)
        self.assertTrue(is_solvable(Board.from_grid(level.grid)))

    def test_build_level_clamps_out_of_range_input(self) -> None:
        level = generator.build_level(99, 1, 999, Difficulty.LOW, random.Random(4))
        self.assertEqual(level.rows, generator.MAX_SIZE)
        self.assertEqual(level.cols, generator.MIN_SIZE)
        self.assertEqual(level.arrow_count, generator.MAX_SIZE * generator.MIN_SIZE)

    def test_build_level_on_a_full_board_is_still_solvable(self) -> None:
        level = generator.build_level(6, 6, 36, Difficulty.HIGH, random.Random(6))
        self.assertEqual(level.arrow_count, 36)
        self.assertTrue(is_solvable(Board.from_grid(level.grid)))

    def test_dense_levels_are_not_trivial(self) -> None:
        """中等以上密度挑出来的关卡，开局总该有箭头被挡住。"""
        for rows, cols, arrows in ((5, 5, 12), (6, 6, 15), (4, 4, 8)):
            with self.subTest(size=(rows, cols), arrows=arrows):
                level = generator.build_level(rows, cols, arrows, Difficulty.HIGH, random.Random(11))
                stats = describe(Board.from_grid(level.grid))
                self.assertGreater(stats["blocked_at_start"], 0)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()