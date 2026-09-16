"""生成 README 与博客用的界面截图。

使用 SDL 的 dummy 驱动离屏渲染，不需要真实显示器，也不需要人工操作：

    python tools/capture_screens.py

输出目录：docs/screenshots/
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from game.app import Game  # noqa: E402
from game.session import Phase  # noqa: E402
from game.solver import solve  # noqa: E402
from game.ui import layout  # noqa: E402

OUTPUT_DIR = ROOT / "docs" / "screenshots"


def first_blocked(session) -> tuple[int, int] | None:
    """找到一个当前被挡住的箭头。"""
    for row, col, _ in list(session.board.iter_arrows()):
        if not session.board.is_free(row, col):
            return row, col
    return None


def first_free(session) -> tuple[int, int] | None:
    for row, col, _ in list(session.board.iter_arrows()):
        if session.board.is_free(row, col):
            return row, col
    return None


def clear_current_level(session) -> None:
    """用求解器给出的顺序自动通关当前关卡。"""
    while session.phase is Phase.PLAYING:
        order = solve(session.board)
        if not order:
            raise RuntimeError("当前关卡无解，关卡数据有问题")
        session.click_cell(*order[0])



def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    game = Game(headless=True)
    session = game.session
    screen = game.screens.game_screen

    def shoot(name: str) -> None:
        path = OUTPUT_DIR / name
        game.save_screenshot(path)
        print(f"已生成 {path.relative_to(ROOT).as_posix()}")

    # 1. 开始界面
    shoot("01-start.png")

    # 2. 选关界面：鼠标悬停在第 4 关那一行
    session.open_level_select()
    game.screens.update(0.0)
    start_screen = game.screens.start_screen
    start_screen.pointer = start_screen.level_row_rect(3).center
    shoot("01b-level-select.png")
    session.back_to_menu()

    # 3. 游戏界面：第 1 关，鼠标悬停在可以飞出的箭头上
    session.start_game()
    game.screens.update(0.0)
    free_cell = first_free(session)
    board_rect = layout.board_rect(session.board.rows, session.board.cols)
    screen.pointer = layout.cell_rect(board_rect, *free_cell).center
    shoot("02-gameplay.png")

    # 4. 碰撞反馈：点击一个被挡住的箭头
    blocked_cell = first_blocked(session)
    screen.click_cell(*blocked_cell)
    shoot("03-blocked.png")

    # 5. 第 3 关进行中
    session.restart_level()
    screen.animations.clear()
    clear_current_level(session)
    session.next_level()
    clear_current_level(session)
    session.next_level()
    for _ in range(3):
        cell = first_free(session)
        screen.click_cell(*cell)
    screen.animations.clear()
    screen.pointer = layout.cell_rect(
        layout.board_rect(session.board.rows, session.board.cols), *first_free(session)
    ).center
    shoot("04-level3.png")

    # 6. 过关面板
    clear_current_level(session)
    screen.animations.clear()
    shoot("05-level-clear.png")

    # 7. 失败面板
    screen.manager.restart_level()
    session.mistakes_left = 1
    blocked_cell = first_blocked(session)
    screen.click_cell(*blocked_cell)
    screen.animations.clear()
    shoot("06-failed.png")

    # 8. 全部通关
    session.restart_level()
    screen.animations.clear()
    while session.phase is not Phase.ALL_CLEAR:
        if session.phase is Phase.PLAYING:
            clear_current_level(session)
        else:
            session.next_level()
    shoot("07-all-clear.png")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())