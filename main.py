"""程序入口：``python main.py``。"""

from __future__ import annotations

from game.app import Game


def main() -> int:
    Game().run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())