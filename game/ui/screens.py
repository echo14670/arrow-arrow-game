"""界面：开始界面、游戏界面、结果界面。

界面只负责「把 Session 的状态画出来」和「把鼠标事件翻译成 Session 的
调用」，游戏规则全部在 :mod:`game.session` 里，方便单独做自动化测试。
"""

from __future__ import annotations

import pygame

from .. import config
from ..direction import Direction
from ..session import ClickResult, Phase, Session, format_time
from . import arrow, layout, theme
from .animations import AnimationManager, Collision, FloatingText, FlyOut
from .widgets import Button

HUD_RECT = pygame.Rect(24, 20, config.WINDOW_WIDTH - 48, 132)
BUTTON_ROW_TOP = 652
OVERLAY_RECT = pygame.Rect(250, 170, 400, 380)
FINAL_RECT = pygame.Rect(150, 120, 600, 480)
LEVEL_SELECT_RECT = pygame.Rect(140, 96, 620, 528)
LEVEL_ROW_HEIGHT = 44
LEVEL_ROW_GAP = 8


class Screen:
    """界面基类。"""

    def __init__(self, session: Session, manager: "ScreenManager") -> None:
        self.session = session
        self.manager = manager
        self.buttons: list[Button] = []
        self.pointer: tuple[int, int] = (config.WINDOW_WIDTH // 2, config.WINDOW_HEIGHT // 2)

    def active_buttons(self) -> list[Button]:
        return self.buttons

    def handle_event(self, event: pygame.event.Event) -> bool:
        for button in self.active_buttons():
            if button.handle_event(event):
                button.action()
                return True
        return False

    def update(self, dt: float) -> None:
        self.pointer = pygame.mouse.get_pos()

    def draw(self, surface: pygame.Surface) -> None:  # pragma: no cover - 抽象
        raise NotImplementedError

    def draw_buttons(self, surface: pygame.Surface) -> None:
        for button in self.active_buttons():
            button.draw(surface)


class StartScreen(Screen):
    """开始界面：标题、玩法说明、开始 / 选关按钮，以及选关面板。"""

    RULES = (
        "棋盘上散布着朝向上、下、左、右的箭头。",
        "点击箭头：它前方到棋盘边界之间没有别的箭头，就会飞出去消失。",
        "如果前方被别的箭头挡住，箭头飞不出去，并消耗一次失误机会。",
        "失误次数耗尽本关失败；清空全部箭头即可进入下一关。",
        "关卡内可以撤销上一步，随时重新开始。",
    )

    def __init__(self, session: Session, manager: "ScreenManager") -> None:
        super().__init__(session, manager)
        width = config.WINDOW_WIDTH
        self.btn_start = Button(
            "开始游戏",
            (width // 2 - 254, 572, 240, 58),
            manager.start_game,
            primary=True,
            font_size=config.FONT_SIZE_H1,
        )
        self.btn_level_select = Button(
            "选择关卡 (L)",
            (width // 2 + 14, 572, 240, 58),
            manager.open_level_select,
            font_size=config.FONT_SIZE_H1,
        )
        self.btn_back = Button(
            "返回主菜单 (L)",
            (LEVEL_SELECT_RECT.centerx - 130, LEVEL_SELECT_RECT.bottom - 72, 260, 46),
            manager.back_to_menu,
        )
        self.buttons = [self.btn_start, self.btn_level_select]

    # ---------- 选关面板 ----------

    @staticmethod
    def level_row_rect(index: int) -> pygame.Rect:
        """选关面板里第 index 行（从 0 开始）的矩形。"""
        top = LEVEL_SELECT_RECT.top + 120 + index * (LEVEL_ROW_HEIGHT + LEVEL_ROW_GAP)
        return pygame.Rect(
            LEVEL_SELECT_RECT.left + 40,
            top,
            LEVEL_SELECT_RECT.width - 80,
            LEVEL_ROW_HEIGHT,
        )

    def level_at(self, pos: tuple[int, int]) -> int | None:
        """鼠标落在第几关的行上；不在任何一行上返回 None。"""
        for index in range(self.session.level_count):
            if self.level_row_rect(index).collidepoint(pos):
                return index
        return None

    def active_buttons(self) -> list[Button]:
        if self.session.phase is Phase.LEVEL_SELECT:
            return [self.btn_back]
        return [self.btn_start, self.btn_level_select]

    # ---------- 事件 ----------

    def handle_event(self, event: pygame.event.Event) -> bool:
        phase = self.session.phase
        if event.type == pygame.KEYDOWN and self._handle_key(event.key, phase):
            return True
        if (
            phase is Phase.LEVEL_SELECT
            and event.type == pygame.MOUSEBUTTONDOWN
            and event.button == 1
        ):
            index = self.level_at(event.pos)
            if index is not None:
                self.manager.start_at_level(index)
                return True
        return super().handle_event(event)

    def _handle_key(self, key: int, phase: Phase) -> bool:
        if phase is Phase.START:
            if key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                self.manager.start_game()
                return True
            if key == pygame.K_l:
                self.manager.open_level_select()
                return True
        elif phase is Phase.LEVEL_SELECT:
            if key == pygame.K_l:
                self.manager.back_to_menu()
                return True
            if pygame.K_1 <= key <= pygame.K_9:
                index = key - pygame.K_1
                if index < self.session.level_count:
                    self.manager.start_at_level(index)
                    return True
        return False

    # ---------- 绘制 ----------

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill(config.COLOR_BACKGROUND)
        if self.session.phase is Phase.LEVEL_SELECT:
            self.draw_level_select(surface)
            self.draw_buttons(surface)
            return
        width = config.WINDOW_WIDTH
        theme.draw_text(
            surface,
            "一箭又一箭",
            config.FONT_SIZE_TITLE,
            config.COLOR_ACCENT,
            center=(width // 2, 96),
        )
        theme.draw_text(
            surface,
            "点击箭头，让棋盘上的箭头全部飞出去",
            config.FONT_SIZE_BODY,
            config.COLOR_TEXT_DIM,
            center=(width // 2, 150),
        )

        panel = pygame.Rect(130, 196, width - 260, 340)
        pygame.draw.rect(surface, config.COLOR_PANEL, panel, border_radius=18)
        pygame.draw.rect(surface, config.COLOR_BORDER, panel, width=2, border_radius=18)

        demo_y = panel.top + 52
        for index, char in enumerate(("^", ">", "v", "<")):
            image = arrow.arrow_surface(44, Direction.from_char(char), config.COLOR_ACCENT)
            surface.blit(
                image, image.get_rect(center=(panel.centerx - 150 + index * 100, demo_y))
            )

        line_y = demo_y + 56
        for index, text in enumerate(self.RULES):
            theme.draw_text(
                surface,
                text,
                config.FONT_SIZE_SMALL,
                config.COLOR_TEXT if index < 3 else config.COLOR_TEXT_DIM,
                topleft=(panel.left + 46, line_y + index * 36),
            )
        theme.draw_text(
            surface,
            "键盘：Enter 开始 / L 选择关卡 / R 重新开始 / U 撤销 / Esc 退出",
            config.FONT_SIZE_SMALL,
            config.COLOR_TEXT_DIM,
            center=(width // 2, 554),
        )
        self.draw_buttons(surface)

    def draw_level_select(self, surface: pygame.Surface) -> None:
        """选关面板：列出全部关卡，点任意一行就从该关开始。"""
        pygame.draw.rect(surface, config.COLOR_PANEL, LEVEL_SELECT_RECT, border_radius=18)
        pygame.draw.rect(
            surface, config.COLOR_BORDER, LEVEL_SELECT_RECT, width=2, border_radius=18
        )
        theme.draw_text(
            surface,
            "选择关卡",
            config.FONT_SIZE_H1,
            config.COLOR_ACCENT,
            centerx=LEVEL_SELECT_RECT.centerx,
            top=LEVEL_SELECT_RECT.top + 30,
        )
        theme.draw_text(
            surface,
            "点击任意一关直接开始，也可以按数字键 1 - 6",
            config.FONT_SIZE_SMALL,
            config.COLOR_TEXT_DIM,
            centerx=LEVEL_SELECT_RECT.centerx,
            top=LEVEL_SELECT_RECT.top + 82,
        )
        hovered = self.level_at(self.pointer)
        for index, level in enumerate(self.session.levels):
            rect = self.level_row_rect(index)
            if index == hovered:
                pygame.draw.rect(surface, config.COLOR_PANEL_LIGHT, rect, border_radius=10)
                pygame.draw.rect(surface, config.COLOR_ACCENT, rect, width=2, border_radius=10)
            else:
                pygame.draw.rect(surface, config.COLOR_BACKGROUND, rect, border_radius=10)
                pygame.draw.rect(surface, config.COLOR_BORDER, rect, width=2, border_radius=10)
            theme.draw_text(
                surface,
                level.name,
                config.FONT_SIZE_BODY,
                config.COLOR_TEXT,
                topleft=(rect.left + 20, rect.centery - 15),
            )
            theme.draw_text(
                surface,
                f"{level.rows}×{level.cols} · {level.arrow_count} 箭头 · 失误 {level.mistakes}",
                config.FONT_SIZE_SMALL,
                config.COLOR_TEXT_DIM,
                topright=(rect.right - 20, rect.centery - 13),
            )

class GameScreen(Screen):
    """游戏界面：HUD + 棋盘 + 结果面板。"""

    def __init__(self, session: Session, manager: "ScreenManager") -> None:
        super().__init__(session, manager)
        self.animations: AnimationManager = manager.animations
        center_x = config.WINDOW_WIDTH // 2
        self.btn_restart = Button(
            "重新开始 (R)", (center_x - 200, BUTTON_ROW_TOP, 190, 46), manager.restart_level
        )
        self.btn_undo = Button("撤销 (U)", (center_x + 10, BUTTON_ROW_TOP, 190, 46), manager.undo)
        panel = OVERLAY_RECT
        self.btn_next = Button(
            "下一关 (Enter)",
            (panel.centerx - 120, panel.bottom - 76, 240, 48),
            manager.next_level,
            primary=True,
        )
        self.btn_retry = Button(
            "重试本关 (R)",
            (panel.centerx - 120, panel.bottom - 76, 240, 48),
            manager.restart_level,
            primary=True,
        )
        self.btn_menu = Button(
            "返回主菜单",
            (panel.centerx - 120, panel.bottom - 136, 240, 44),
            manager.back_to_menu,
        )
        final = FINAL_RECT
        self.btn_again = Button(
            "再玩一次 (Enter)",
            (final.centerx - 130, final.bottom - 100, 260, 52),
            manager.start_game,
            primary=True,
        )
        self.btn_menu_final = Button(
            "返回主菜单",
            (final.centerx - 130, final.bottom - 160, 260, 46),
            manager.back_to_menu,
        )

    # ---------- 事件 ----------

    def active_buttons(self) -> list[Button]:
        phase = self.session.phase
        if phase is Phase.PLAYING:
            return [self.btn_restart, self.btn_undo]
        if phase is Phase.LEVEL_CLEAR:
            return [self.btn_next, self.btn_menu]
        if phase is Phase.FAILED:
            return [self.btn_retry, self.btn_menu]
        if phase is Phase.ALL_CLEAR:
            return [self.btn_again, self.btn_menu_final]
        return []

    def handle_event(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.KEYDOWN and self._handle_key(event.key):
            return True
        if self.animations.busy and event.type == pygame.MOUSEBUTTONDOWN:
            return False
        if super().handle_event(event):
            return True
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.session.phase is Phase.PLAYING:
                cell = layout.cell_at(event.pos, self.session.board.rows, self.session.board.cols)
                if cell is not None:
                    self.click_cell(cell[0], cell[1])
                    return True
        return False

    def _handle_key(self, key: int) -> bool:
        phase = self.session.phase
        if key == pygame.K_r and phase in (Phase.PLAYING, Phase.LEVEL_CLEAR, Phase.FAILED):
            self.manager.restart_level()
            return True
        if key == pygame.K_u and phase is Phase.PLAYING:
            self.manager.undo()
            return True
        if key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
            if phase is Phase.LEVEL_CLEAR:
                self.manager.next_level()
                return True
            if phase is Phase.ALL_CLEAR:
                self.manager.start_game()
                return True
        return False

    def click_cell(self, row: int, col: int) -> ClickResult:
        """点击某一格，并根据结果播放对应动画。"""
        board = self.session.board
        if not board.has_arrow(row, col):
            return ClickResult.IGNORED
        direction = board.at(row, col)
        result = self.session.click_cell(row, col)
        board_rect = layout.board_rect(board.rows, board.cols)
        cell = layout.cell_rect(board_rect, row, col)
        now = pygame.time.get_ticks() / 1000.0
        if result is ClickResult.REMOVED:
            self.animations.add(FlyOut(now, board_rect, row, col, direction))
        elif result is ClickResult.BLOCKED:
            self.animations.add(Collision(now, board_rect, row, col, direction))
            self.animations.add(
                FloatingText(now, "被挡住了！", (cell.centerx, cell.top - 6), config.COLOR_DANGER)
            )
        return result

    def update(self, dt: float) -> None:
        super().update(dt)
        self.animations.update(pygame.time.get_ticks() / 1000.0)
        self.btn_undo.enabled = self.session.can_undo

    # ---------- 绘制 ----------

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill(config.COLOR_BACKGROUND)
        self.draw_hud(surface)
        self.draw_board(surface)
        self.animations.draw(surface, pygame.time.get_ticks() / 1000.0)
        phase = self.session.phase
        if self.animations.busy:
            if phase is Phase.PLAYING:
                self.btn_restart.draw(surface)
                self.btn_undo.draw(surface)
            return
        if phase is Phase.LEVEL_CLEAR:
            self.draw_level_clear(surface)
        elif phase is Phase.FAILED:
            self.draw_failed(surface)
        elif phase is Phase.ALL_CLEAR:
            self.draw_all_clear(surface)
        self.draw_buttons(surface)

    def draw_hud(self, surface: pygame.Surface) -> None:
        session = self.session
        pygame.draw.rect(surface, config.COLOR_PANEL, HUD_RECT, border_radius=16)
        pygame.draw.rect(surface, config.COLOR_BORDER, HUD_RECT, width=2, border_radius=16)
        theme.draw_text(
            surface, session.level.name, config.FONT_SIZE_H1, config.COLOR_TEXT, topleft=(48, 40)
        )
        theme.draw_text(
            surface,
            f"关卡 {session.level_number} / {session.level_count}",
            config.FONT_SIZE_BODY,
            config.COLOR_TEXT_DIM,
            topright=(HUD_RECT.right - 24, 36),
        )
        theme.draw_text(
            surface,
            f"用时 {format_time(session.level_time)}",
            config.FONT_SIZE_BODY,
            config.COLOR_TEXT_DIM,
            topright=(HUD_RECT.right - 24, 72),
        )
        theme.draw_text(
            surface,
            f"剩余箭头 {session.arrows_left} / {session.arrows_total}",
            config.FONT_SIZE_HUD,
            config.COLOR_ACCENT,
            topleft=(48, 104),
        )
        mistake_color = config.COLOR_DANGER if session.mistakes_left <= 1 else config.COLOR_TEXT
        theme.draw_text(
            surface,
            f"失误 {session.mistakes_left} / {session.mistakes_total}",
            config.FONT_SIZE_HUD,
            mistake_color,
            centerx=HUD_RECT.centerx,
            top=104,
        )

    def draw_board(self, surface: pygame.Surface) -> None:
        session = self.session
        board = session.board
        board_rect = layout.board_rect(board.rows, board.cols)
        hover: tuple[int, int] | None = None
        if session.phase is Phase.PLAYING:
            hover = layout.cell_at(self.pointer, board.rows, board.cols)
        for row in range(board.rows):
            for col in range(board.cols):
                cell = layout.cell_rect(board_rect, row, col)
                pygame.draw.rect(surface, config.COLOR_PANEL_LIGHT, cell, border_radius=12)
                border = config.COLOR_BORDER
                if hover == (row, col) and board.has_arrow(row, col):
                    border = config.COLOR_HOVER
                pygame.draw.rect(surface, border, cell, width=2, border_radius=12)
        for row, col, direction in list(board.iter_arrows()):
            color = (
                config.COLOR_ACCENT_BRIGHT
                if hover == (row, col)
                else config.COLOR_ACCENT
            )
            image = arrow.arrow_surface(config.CELL_SIZE, direction, color)
            surface.blit(image, layout.cell_rect(board_rect, row, col).topleft)

    def draw_overlay(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        layer = pygame.Surface((config.WINDOW_WIDTH, config.WINDOW_HEIGHT), pygame.SRCALPHA)
        layer.fill((0, 0, 0, 150))
        surface.blit(layer, (0, 0))
        pygame.draw.rect(surface, config.COLOR_PANEL, rect, border_radius=18)
        pygame.draw.rect(surface, config.COLOR_BORDER, rect, width=2, border_radius=18)

    def draw_level_clear(self, surface: pygame.Surface) -> None:
        session = self.session
        self.draw_overlay(surface, OVERLAY_RECT)
        theme.draw_text(
            surface,
            "过关！",
            config.FONT_SIZE_H1,
            config.COLOR_SUCCESS,
            centerx=OVERLAY_RECT.centerx,
            top=OVERLAY_RECT.top + 34,
        )
        lines = (
            f"用时 {format_time(session.level_time)}",
            f"点击 {session.level_clicks} 次",
            f"失误 {session.level_mistakes} 次",
            f"撤销 {session.level_undos} 次",
        )
        for index, text in enumerate(lines):
            theme.draw_text(
                surface,
                text,
                config.FONT_SIZE_BODY,
                config.COLOR_TEXT,
                centerx=OVERLAY_RECT.centerx,
                top=OVERLAY_RECT.top + 100 + index * 34,
            )

    def draw_failed(self, surface: pygame.Surface) -> None:
        session = self.session
        self.draw_overlay(surface, OVERLAY_RECT)
        theme.draw_text(
            surface,
            "本关失败",
            config.FONT_SIZE_H1,
            config.COLOR_DANGER,
            centerx=OVERLAY_RECT.centerx,
            top=OVERLAY_RECT.top + 34,
        )
        lines = (
            "失误次数已经用尽",
            f"还剩下 {session.arrows_left} 个箭头",
            f"用时 {format_time(session.level_time)}",
        )
        for index, text in enumerate(lines):
            theme.draw_text(
                surface,
                text,
                config.FONT_SIZE_BODY,
                config.COLOR_TEXT,
                centerx=OVERLAY_RECT.centerx,
                top=OVERLAY_RECT.top + 100 + index * 34,
            )

    def draw_all_clear(self, surface: pygame.Surface) -> None:
        session = self.session
        self.draw_overlay(surface, FINAL_RECT)
        theme.draw_text(
            surface,
            "全部通关！",
            config.FONT_SIZE_TITLE,
            config.COLOR_SUCCESS,
            centerx=FINAL_RECT.centerx,
            top=FINAL_RECT.top + 40,
        )
        lines = (
            f"通关 {session.cleared_levels} / {session.level_count} 关",
            f"总用时 {format_time(session.total_time)}",
            f"总点击 {session.total_clicks} 次，失误 {session.total_mistakes} 次",
            f"总共撤销 {session.total_undos} 次",
        )
        for index, text in enumerate(lines):
            theme.draw_text(
                surface,
                text,
                config.FONT_SIZE_BODY,
                config.COLOR_TEXT,
                centerx=FINAL_RECT.centerx,
                top=FINAL_RECT.top + 120 + index * 40,
            )


class ScreenManager:
    """根据 :class:`Phase` 分发界面，并集中处理流程动作。"""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.animations = AnimationManager()
        self.start_screen = StartScreen(session, self)
        self.game_screen = GameScreen(session, self)

    @property
    def current(self) -> Screen:
        if self.session.phase in (Phase.START, Phase.LEVEL_SELECT):
            return self.start_screen
        return self.game_screen

    def handle_event(self, event: pygame.event.Event) -> bool:
        return self.current.handle_event(event)

    def update(self, dt: float) -> None:
        self.current.update(dt)

    def draw(self, surface: pygame.Surface) -> None:
        self.current.draw(surface)

    # ---------- 动作 ----------

    def start_game(self) -> None:
        self.animations.clear()
        self.session.start_game()

    def open_level_select(self) -> None:
        self.animations.clear()
        self.session.open_level_select()

    def start_at_level(self, index: int) -> None:
        self.animations.clear()
        self.session.start_at_level(index)

    def restart_level(self) -> None:
        self.animations.clear()
        self.session.restart_level()

    def next_level(self) -> None:
        self.animations.clear()
        self.session.next_level()

    def back_to_menu(self) -> None:
        self.animations.clear()
        self.session.back_to_menu()

    def undo(self) -> None:
        self.session.undo()