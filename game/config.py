"""全局配置：窗口尺寸、配色、字体与动画参数。"""

from __future__ import annotations

WINDOW_TITLE = "一箭又一箭"
WINDOW_WIDTH = 900
WINDOW_HEIGHT = 720
FPS = 60

# 棋盘格子尺寸（按最大 6x6 棋盘设计：6 * 72 + 5 * 7 = 467）
CELL_SIZE = 72
CELL_GAP = 7
BOARD_TOP = 172
BOARD_MAX_SIZE = 6

# 动画时长（秒）
FLY_DURATION = 0.30
SHAKE_DURATION = 0.36
FLASH_DURATION = 0.60
TEXT_FLOAT_DURATION = 0.75
SHAKE_AMPLITUDE = 9

# 配色
COLOR_BACKGROUND = (22, 26, 38)
COLOR_PANEL = (34, 40, 58)
COLOR_PANEL_LIGHT = (46, 54, 78)
COLOR_BORDER = (72, 84, 116)
COLOR_TEXT = (232, 236, 248)
COLOR_TEXT_DIM = (150, 160, 186)
COLOR_ACCENT = (236, 196, 96)
COLOR_ACCENT_BRIGHT = (255, 232, 150)
COLOR_DANGER = (232, 86, 86)
COLOR_SUCCESS = (104, 200, 132)
COLOR_HOVER = (255, 255, 255)

# 字体（按顺序尝试，找不到就用 pygame 默认字体）
FONT_CANDIDATES = (
    r"C:\Windows\Fonts\msyh.ttc",
    r"C:\Windows\Fonts\msyh.ttf",
    r"C:\Windows\Fonts\simhei.ttf",
    r"C:\Windows\Fonts\simsun.ttc",
    r"C:\Windows\Fonts\Deng.ttf",
)
SYS_FONT_CANDIDATES = ("microsoftyahei", "microsoftyaheiui", "simhei", "simsun", "dengxian")

FONT_SIZE_TITLE = 52
FONT_SIZE_H1 = 34
FONT_SIZE_BODY = 24
FONT_SIZE_SMALL = 20
FONT_SIZE_HUD = 26