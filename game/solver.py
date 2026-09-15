"""关卡求解器：判断一关能否通关，并给出一个可行的消除顺序。"""

from __future__ import annotations

from .board import Board


def solve(board: Board) -> list[tuple[int, int]] | None:
    """返回一个可行的消除顺序；无解时返回 None。

    移除箭头只会让别的箭头更加自由，所以「当前能否通关」这件事是单调
    的：任何时刻随便挑一个前方无阻挡的箭头拿走都不会把自己走死。因此
    不需要回溯，逐步贪心即可，复杂度约为 O(箭头数^2)。
    """
    working = board.copy()
    order: list[tuple[int, int]] = []
    while working.arrow_count:
        for row, col, _ in list(working.iter_arrows()):
            if working.is_free(row, col):
                working.remove(row, col)
                order.append((row, col))
                break
        else:
            return None
    return order


def is_solvable(board: Board) -> bool:
    """关卡是否存在至少一种通关顺序。"""
    return solve(board) is not None


def describe(board: Board) -> dict[str, int]:
    """统计关卡特征，用于生成关卡时挑选手感更好的布局。

    - ``blocked_at_start``: 开局就被挡住的箭头数量
    - ``forced_steps``: 只有唯一选择（不能不点它）的步数
    - ``choice_steps``: 有多个可选箭头的步数
    - ``solvable``: 是否可解（1/0）
    """
    working = board.copy()
    blocked = sum(
        1 for row, col, _ in list(working.iter_arrows()) if not working.is_free(row, col)
    )
    forced_steps = 0
    choice_steps = 0
    while working.arrow_count:
        free = [
            (row, col) for row, col, _ in list(working.iter_arrows()) if working.is_free(row, col)
        ]
        if not free:
            return {
                "arrow_count": board.arrow_count,
                "blocked_at_start": blocked,
                "forced_steps": -1,
                "choice_steps": -1,
                "solvable": 0,
            }
        if len(free) == 1:
            forced_steps += 1
        else:
            choice_steps += 1
        working.remove(*free[0])
    return {
        "arrow_count": board.arrow_count,
        "blocked_at_start": blocked,
        "forced_steps": forced_steps,
        "choice_steps": choice_steps,
        "solvable": 1,
    }