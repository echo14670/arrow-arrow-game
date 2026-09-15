"""棋盘与格子的屏幕坐标计算。"""

from __future__ import annotations

import pygame

from .. import config


def board_size(rows: int, cols: int) -> tuple[int, int]:
    """棋盘像素尺寸。"""
    width = cols * config.CELL_SIZE + max(0, cols - 1) * config.CELL_GAP
    height = rows * config.CELL_SIZE + max(0, rows - 1) * config.CELL_GAP
    return width, height


def board_rect(rows: int, cols: int) -> pygame.Rect:
    """棋盘在窗口中的位置（水平居中）。"""
    width, height = board_size(rows, cols)
    left = (config.WINDOW_WIDTH - width) // 2
    return pygame.Rect(left, config.BOARD_TOP, width, height)


def cell_rect(board: pygame.Rect, row: int, col: int) -> pygame.Rect:
    """某个格子的矩形。"""
    left = board.left + col * (config.CELL_SIZE + config.CELL_GAP)
    top = board.top + row * (config.CELL_SIZE + config.CELL_GAP)
    return pygame.Rect(left, top, config.CELL_SIZE, config.CELL_SIZE)


def cell_at(pos: tuple[int, int], rows: int, cols: int) -> tuple[int, int] | None:
    """把鼠标坐标换算成格子坐标；不在棋盘内返回 None。"""
    board = board_rect(rows, cols)
    if not board.collidepoint(pos):
        return None
    step = config.CELL_SIZE + config.CELL_GAP
    col, offset_x = divmod(pos[0] - board.left, step)
    row, offset_y = divmod(pos[1] - board.top, step)
    if offset_x >= config.CELL_SIZE or offset_y >= config.CELL_SIZE:
        return None
    if not (0 <= row < rows and 0 <= col < cols):
        return None
    return row, col