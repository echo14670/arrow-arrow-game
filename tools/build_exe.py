"""一键把游戏打包成 Windows 可执行文件。

    python tools/build_exe.py

会在 dist/ 目录下生成单文件、无控制台窗口的 ArrowArrowGame.exe。
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAME = "ArrowArrowGame"


def main() -> int:
    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--windowed",
        "--onefile",
        "--name",
        NAME,
        str(ROOT / "main.py"),
    ]
    print("执行：" + " ".join(command))
    result = subprocess.run(command, cwd=ROOT)
    if result.returncode != 0:
        print("打包失败，请检查 PyInstaller 是否已安装（pip install pyinstaller）")
        return result.returncode
    print(f"打包完成：dist/{NAME}.exe")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())