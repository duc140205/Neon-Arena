"""
ui.py - HUD, Level-up screen, Game Over, and Menu rendering
All positions use self.W/self.H (actual display resolution).
Font sizes are scaled for native-resolution rendering.
"""

import pygame
import math
import random
from .settings import (
    SCREEN_WIDTH, SCREEN_HEIGHT,
    ARENA_WIDTH, ARENA_HEIGHT,
    NEON_CYAN, NEON_MAGENTA, NEON_PINK, NEON_YELLOW, NEON_GREEN, NEON_PURPLE, NEON_RED,
    NEON_ORANGE,
    WHITE, BLACK, DARK_BG, GRAY, DARK_GRAY,
    HP_BAR, HP_BAR_BG, XP_BAR, XP_BAR_BG,
    UPGRADES,
    POWERUP_TYPES,
)


class UI:
    """Handles all user interface rendering at native resolution."""

    def __init__(self, screen_width=1280, screen_height=720):
        pygame.font.init()
        self.W = screen_width
        self.H = screen_height
        self.scale = screen_width / 1280  # relative to base 720p

        # Create fonts scaled to current resolution
        self._create_fonts()

        self.upgrade_rects = []
        self.scanline_alpha = 20

        # Menu button rects (set during draw)
        self.menu_start_rect = pygame.Rect(0, 0, 0, 0)
        self.menu_settings_rect = pygame.Rect(0, 0, 0, 0)
        self.menu_quit_rect = pygame.Rect(0, 0, 0, 0)

    def _create_fonts(self):
        """Create fonts scaled to the current resolution."""
        s = self.scale
        try:
            self.font_large = pygame.font.SysFont("consolas", max(12, int(48 * s)), bold=True)
            self.font_medium = pygame.font.SysFont("consolas", max(10, int(28 * s)), bold=True)
            self.font_small = pygame.font.SysFont("consolas", max(8, int(18 * s)))
            self.font_tiny = pygame.font.SysFont("consolas", max(7, int(14 * s)))
            self.font_title = pygame.font.SysFont("consolas", max(16, int(72 * s)), bold=True)
        except Exception:
            self.font_large = pygame.font.Font(None, max(12, int(48 * s)))
            self.font_medium = pygame.font.Font(None, max(10, int(28 * s)))
            self.font_small = pygame.font.Font(None, max(8, int(18 * s)))
            self.font_tiny = pygame.font.Font(None, max(7, int(14 * s)))
            self.font_title = pygame.font.Font(None, max(16, int(72 * s)))

    def _s(self, pixels):
        """Scale a base-720p pixel value to current resolution."""
        return max(1, int(pixels * self.scale))

    def draw_hud(self, surface, player, wave_info, fps):
        """Draw the in-game HUD overlay."""
        s = self._s
        W, H = self.W, self.H

        # ── HP Bar (top-left) ──
        bar_x, bar_y = s(20), s(20)
        bar_w, bar_h = s(250), s(20)
        self._draw_rounded_bar(surface, bar_x, bar_y, bar_w, bar_h, HP_BAR_BG)
        hp_ratio = max(0, player.hp / player.max_hp)
        fill_w = int(bar_w * hp_ratio)
        if fill_w > 0:
            if hp_ratio > 0.5:
                color = HP_BAR
            elif hp_ratio > 0.25:
                color = NEON_YELLOW
            else:
                color = NEON_RED
            self._draw_rounded_bar(surface, bar_x, bar_y, fill_w, bar_h, color)
        pygame.draw.rect(surface, NEON_PINK, (bar_x, bar_y, bar_w, bar_h), max(1, s(2)), border_radius=s(4))
        hp_text = self.font_small.render(f"HP {player.hp}/{player.max_hp}", True, WHITE)
        surface.blit(hp_text, (bar_x + bar_w + s(10), bar_y + s(1)))

        # ── XP Bar ──
        xp_y = bar_y + bar_h + s(8)
        xp_w, xp_h = s(250), s(12)
        self._draw_rounded_bar(surface, bar_x, xp_y, xp_w, xp_h, XP_BAR_BG)
        xp_ratio = min(1.0, player.xp / max(1, player.xp_required))
        xp_fill = int(xp_w * xp_ratio)
        if xp_fill > 0:
            self._draw_rounded_bar(surface, bar_x, xp_y, xp_fill, xp_h, XP_BAR)
        pygame.draw.rect(surface, NEON_CYAN, (bar_x, xp_y, xp_w, xp_h), 1, border_radius=s(3))
        lvl_text = self.font_small.render(f"LV {player.level}", True, NEON_CYAN)
        surface.blit(lvl_text, (bar_x + xp_w + s(10), xp_y - s(2)))
        xp_text = self.font_tiny.render(f"{player.xp}/{player.xp_required} XP", True, GRAY)
        surface.blit(xp_text, (bar_x + xp_w + s(60), xp_y))

        # ── Dash Cooldown ──
        dash_y = H - s(50)
        dash_x = s(20)
        dash_w, dash_h = s(120), s(8)
        dash_ratio = max(0, 1.0 - player.dash_cooldown_timer / player.dash_cooldown)
        self._draw_rounded_bar(surface, dash_x, dash_y, dash_w, dash_h, DARK_GRAY)
        if dash_ratio > 0:
            color = NEON_MAGENTA if dash_ratio >= 1.0 else GRAY
            self._draw_rounded_bar(surface, dash_x, dash_y,
                                   int(dash_w * dash_ratio), dash_h, color)
        dash_label = self.font_tiny.render("DASH [SPACE]", True,
                                           NEON_MAGENTA if dash_ratio >= 1.0 else GRAY)
        surface.blit(dash_label, (dash_x, dash_y - s(16)))

        # ── Wave Info (top-right) ──
        wave_text = self.font_medium.render(f"WAVE {wave_info['wave']}", True, NEON_CYAN)
        tr = wave_text.get_rect(topright=(W - s(20), s(20)))
        surface.blit(wave_text, tr)

        enemies_text = self.font_small.render(
            f"Enemies: {wave_info['enemies_alive']}", True, NEON_PINK)
        er = enemies_text.get_rect(topright=(W - s(20), s(55)))
        surface.blit(enemies_text, er)

        kills_text = self.font_tiny.render(
            f"Kills: {wave_info['total_killed']}", True, GRAY)
        kr = kills_text.get_rect(topright=(W - s(20), s(80)))
        surface.blit(kills_text, kr)

        # ── FPS ──
        fps_color = NEON_GREEN if fps >= 55 else NEON_YELLOW if fps >= 30 else (255, 40, 40)
        fps_text = self.font_tiny.render(f"FPS: {fps:.0f}", True, fps_color)
        fr = fps_text.get_rect(topright=(W - s(20), s(100)))
        surface.blit(fps_text, fr)

    def draw_minimap(self, surface, player, obstacles, powerups, enemies, boss=None):
        """Draw a minimap overlay in the bottom-right corner."""
        s = self._s
        W, H = self.W, self.H

        map_w = s(160)
        map_h = s(160)
        margin = s(15)
        map_x = W - map_w - margin
        map_y = H - map_h - margin

        # Scale factors: arena coords -> minimap coords
        sx_ratio = map_w / ARENA_WIDTH
        sy_ratio = map_h / ARENA_HEIGHT

        # Separate alpha surface
        mm_surf = pygame.Surface((map_w, map_h), pygame.SRCALPHA)
        mm_surf.fill((10, 10, 30, 160))

        # Border
        pygame.draw.rect(mm_surf, (*NEON_CYAN, 120), (0, 0, map_w, map_h), max(1, s(1)))

        # Obstacles (gray blocks)
        for obs in obstacles:
            ox = int(obs.x * sx_ratio)
            oy = int(obs.y * sy_ratio)
            ow = max(1, int(obs.w * sx_ratio))
            oh = max(1, int(obs.h * sy_ratio))
            pygame.draw.rect(mm_surf, (60, 60, 80, 180), (ox, oy, ow, oh))

        # Enemies (small red dots)
        for enemy in enemies:
            ex = int(enemy.pos_x * sx_ratio)
            ey = int(enemy.pos_y * sy_ratio)
            is_boss_enemy = hasattr(enemy, 'is_boss') and enemy.is_boss
            if is_boss_enemy:
                # Boss: large pulsing red icon
                pulse = int(2 * math.sin(pygame.time.get_ticks() * 0.008))
                br = max(2, s(5) + pulse)
                pygame.draw.circle(mm_surf, (*NEON_RED, 220), (ex, ey), br)
                pygame.draw.circle(mm_surf, (*NEON_YELLOW, 150), (ex, ey), br, 1)
            else:
                pygame.draw.circle(mm_surf, (*NEON_RED, 180), (ex, ey), max(1, s(2)))

        # Power-ups (colored dots)
        for pu in powerups:
            px = int(pu.pos_x * sx_ratio)
            py = int(pu.pos_y * sy_ratio)
            pygame.draw.circle(mm_surf, (*pu.color, 200), (px, py), max(1, s(3)))

        # Player (bright cyan dot)
        ppx = int(player.pos_x * sx_ratio)
        ppy = int(player.pos_y * sy_ratio)
        pygame.draw.circle(mm_surf, NEON_CYAN, (ppx, ppy), max(2, s(3)))
        # Tiny glow
        glow_r = max(3, s(5))
        glow_surf = pygame.Surface((glow_r * 2, glow_r * 2), pygame.SRCALPHA)
        pygame.draw.circle(glow_surf, (*NEON_CYAN, 60), (glow_r, glow_r), glow_r)
        mm_surf.blit(glow_surf, (ppx - glow_r, ppy - glow_r))

        # Label
        label = self.font_tiny.render("MAP", True, NEON_CYAN)
        mm_surf.blit(label, (s(4), s(2)))

        surface.blit(mm_surf, (map_x, map_y))

    def draw_boss_hp_bar(self, surface, wave_info):
        """Draw a dramatic boss HP bar at the top-center of the screen."""
        if not wave_info.get("boss_active", False):
            return

        s = self._s
        W = self.W

        bar_w = s(500)
        bar_h = s(24)
        bar_x = (W - bar_w) // 2
        bar_y = s(12)

        # Background
        bg_rect = pygame.Rect(bar_x - s(4), bar_y - s(4),
                              bar_w + s(8), bar_h + s(8))
        bg_surf = pygame.Surface((bg_rect.width, bg_rect.height), pygame.SRCALPHA)
        bg_surf.fill((15, 5, 20, 200))
        surface.blit(bg_surf, bg_rect.topleft)
        pygame.draw.rect(surface, NEON_RED, bg_rect, max(1, s(2)), border_radius=s(4))

        # HP fill
        hp_ratio = max(0, wave_info["boss_hp"] / max(1, wave_info["boss_max_hp"]))
        fill_w = int(bar_w * hp_ratio)
        if fill_w > 0:
            # Pulsing intensity
            pulse = 0.8 + 0.2 * math.sin(pygame.time.get_ticks() * 0.006)
            fill_color = (
                int(min(255, NEON_RED[0] * pulse)),
                int(min(255, NEON_RED[1] * pulse)),
                int(min(255, NEON_RED[2] * pulse)),
            )
            self._draw_rounded_bar(surface, bar_x, bar_y, fill_w, bar_h, fill_color)

        # Label
        boss_text = self.font_medium.render("⚠ BOSS ⚠", True, NEON_YELLOW)
        tr = boss_text.get_rect(center=(W // 2, bar_y + bar_h + s(16)))
        surface.blit(boss_text, tr)

        # HP numbers
        hp_nums = self.font_tiny.render(
            f"{wave_info['boss_hp']}/{wave_info['boss_max_hp']}", True, WHITE)
        hr = hp_nums.get_rect(center=(W // 2, bar_y + bar_h // 2))
        surface.blit(hp_nums, hr)

    def draw_wave_announcement(self, surface, wave_num, timer, is_boss=False):
        if timer <= 0:
            return
        W, H = self.W, self.H
        alpha = min(255, int(timer * 255))

        if is_boss:
            text = self.font_large.render(f"// WAVE {wave_num} — BOSS //", True, NEON_RED)
        else:
            text = self.font_large.render(f"// WAVE {wave_num} //", True, NEON_CYAN)
        text.set_alpha(alpha)
        text_rect = text.get_rect(center=(W // 2, H // 2 - self._s(30)))
        surface.blit(text, text_rect)

        sub_msg = "⚠ BOSS FIGHT ⚠" if is_boss else "INCOMING HOSTILES"
        sub_color = NEON_YELLOW if is_boss else NEON_MAGENTA
        sub = self.font_small.render(sub_msg, True, sub_color)
        sub.set_alpha(alpha)
        sub_rect = sub.get_rect(center=(W // 2, H // 2 + self._s(20)))
        surface.blit(sub, sub_rect)

    def draw_upgrade_screen(self, surface, upgrade_options, player, logical_mouse_pos=None):
        W, H = self.W, self.H
        s = self._s

        overlay = pygame.Surface((W, H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        surface.blit(overlay, (0, 0))

        title = self.font_large.render("LEVEL UP!", True, NEON_YELLOW)
        title_rect = title.get_rect(center=(W // 2, s(100)))
        surface.blit(title, title_rect)

        subtitle = self.font_small.render(f"Level {player.level} — Choose an upgrade", True, GRAY)
        sub_rect = subtitle.get_rect(center=(W // 2, s(150)))
        surface.blit(subtitle, sub_rect)

        self.upgrade_rects = []
        card_w = s(280)
        card_h = s(200)
        total_w = len(upgrade_options) * card_w + (len(upgrade_options) - 1) * s(30)
        start_x = (W - total_w) // 2
        card_y = s(200)

        mouse_pos = pygame.mouse.get_pos()

        for i, key in enumerate(upgrade_options):
            upgrade = UPGRADES[key]
            cx = start_x + i * (card_w + s(30))
            card_rect = pygame.Rect(cx, card_y, card_w, card_h)
            self.upgrade_rects.append((card_rect, key))

            is_hovered = card_rect.collidepoint(mouse_pos)

            bg_color = (*upgrade["color"], 30) if not is_hovered else (*upgrade["color"], 60)
            card_surf = pygame.Surface((card_w, card_h), pygame.SRCALPHA)
            card_surf.fill(bg_color)
            surface.blit(card_surf, (cx, card_y))

            border_color = upgrade["color"] if is_hovered else DARK_GRAY
            border_w = max(1, s(3)) if is_hovered else 1
            pygame.draw.rect(surface, border_color, card_rect, border_w, border_radius=s(6))

            icon_text = self.font_large.render(upgrade["icon"], True, upgrade["color"])
            icon_rect = icon_text.get_rect(center=(cx + card_w // 2, card_y + s(50)))
            surface.blit(icon_text, icon_rect)

            name_text = self.font_medium.render(upgrade["name"], True, WHITE)
            name_rect = name_text.get_rect(center=(cx + card_w // 2, card_y + s(100)))
            surface.blit(name_text, name_rect)

            desc_text = self.font_small.render(upgrade["desc"], True, GRAY)
            desc_rect = desc_text.get_rect(center=(cx + card_w // 2, card_y + s(135)))
            surface.blit(desc_text, desc_rect)

            current_lvl = player.upgrade_levels.get(key, 0)
            max_lvl = upgrade["max_level"]
            pip_y = card_y + s(165)
            pip_total_w = max_lvl * s(16)
            pip_start = cx + (card_w - pip_total_w) // 2
            for j in range(max_lvl):
                pip_x = pip_start + j * s(16)
                pip_color = upgrade["color"] if j < current_lvl else DARK_GRAY
                if j == current_lvl:
                    pip_color = NEON_YELLOW
                pygame.draw.rect(surface, pip_color, (pip_x, pip_y, s(12), s(8)),
                                 0, border_radius=s(2))

        instr = self.font_tiny.render("Click to select an upgrade", True, GRAY)
        instr_rect = instr.get_rect(center=(W // 2, card_y + card_h + s(40)))
        surface.blit(instr, instr_rect)

    def draw_game_over(self, surface, player, wave_info):
        W, H = self.W, self.H
        s = self._s

        overlay = pygame.Surface((W, H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        surface.blit(overlay, (0, 0))

        title = self.font_title.render("GAME OVER", True, NEON_RED)
        title_rect = title.get_rect(center=(W // 2, H // 2 - s(80)))
        surface.blit(title, title_rect)

        stats = [
            f"Wave Reached: {wave_info['wave']}",
            f"Total Kills: {wave_info['total_killed']}",
            f"Level: {player.level}",
        ]
        for i, stat in enumerate(stats):
            text = self.font_medium.render(stat, True, NEON_CYAN)
            rect = text.get_rect(center=(W // 2, H // 2 + i * s(40)))
            surface.blit(text, rect)

        restart = self.font_small.render("[R] Restart  |  [ESC] Quit", True, GRAY)
        r_rect = restart.get_rect(center=(W // 2, H // 2 + s(160)))
        surface.blit(restart, r_rect)

    def draw_main_menu(self, surface, time, logical_mouse_pos=None):
        W, H = self.W, self.H
        s = self._s
        surface.fill(DARK_BG)

        # Animated grid
        grid_step = max(4, s(60))
        for x in range(0, W, grid_step):
            alpha = int(20 + 10 * math.sin(time * 2 + x * 0.01))
            line_surf = pygame.Surface((1, H), pygame.SRCALPHA)
            line_surf.fill((0, 255, 255, alpha))
            surface.blit(line_surf, (x, 0))
        for y in range(0, H, grid_step):
            alpha = int(20 + 10 * math.sin(time * 2 + y * 0.01))
            line_surf = pygame.Surface((W, 1), pygame.SRCALPHA)
            line_surf.fill((255, 0, 200, alpha))
            surface.blit(line_surf, (0, y))

        # Title
        title = self.font_title.render("NEON ARENA", True, NEON_CYAN)
        glow_title = self.font_title.render("NEON ARENA", True, (*NEON_CYAN, 30))
        title_y = s(180)
        title_rect = title.get_rect(center=(W // 2, title_y))
        for dx, dy in [(2, 2), (-2, -2), (2, -2), (-2, 2)]:
            glow_rect = glow_title.get_rect(center=(W // 2 + dx, title_y + dy))
            surface.blit(glow_title, glow_rect)
        surface.blit(title, title_rect)

        # Subtitle
        sub = self.font_medium.render("// CYBERPUNK SHOOTER //", True, NEON_MAGENTA)
        sub_rect = sub.get_rect(center=(W // 2, s(250)))
        surface.blit(sub, sub_rect)

        # ── Menu Buttons ──
        mouse_pos = pygame.mouse.get_pos()
        button_w, button_h = s(280), s(48)
        button_x = (W - button_w) // 2
        btn_y = s(320)

        # Start
        start_rect = pygame.Rect(button_x, btn_y, button_w, button_h)
        self._draw_menu_button(surface, "START GAME", start_rect,
                               start_rect.collidepoint(mouse_pos), NEON_GREEN, time)
        self.menu_start_rect = start_rect

        # Settings
        settings_rect = pygame.Rect(button_x, btn_y + s(65), button_w, button_h)
        self._draw_menu_button(surface, "SETTINGS", settings_rect,
                               settings_rect.collidepoint(mouse_pos), NEON_CYAN, time)
        self.menu_settings_rect = settings_rect

        # Quit
        quit_rect = pygame.Rect(button_x, btn_y + s(130), button_w, button_h)
        self._draw_menu_button(surface, "QUIT", quit_rect,
                               quit_rect.collidepoint(mouse_pos), NEON_PINK, time)
        self.menu_quit_rect = quit_rect

        # Controls
        controls = self.font_tiny.render(
            "WASD — Move    |    Mouse — Aim & Shoot    |    Space — Dash", True, GRAY)
        ctrl_rect = controls.get_rect(center=(W // 2, btn_y + s(220)))
        surface.blit(controls, ctrl_rect)

        self._draw_scanlines(surface)

    def _draw_menu_button(self, surface, label, rect, hovered, accent_color, time):
        s = self._s
        if hovered:
            pulse = int(15 * math.sin(time * 5))
            bg_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            bg_surf.fill((*accent_color, 35 + pulse))
            surface.blit(bg_surf, rect.topleft)
            pygame.draw.line(surface, accent_color,
                             (rect.left, rect.top), (rect.left, rect.bottom), max(1, s(3)))

        border_color = accent_color if hovered else DARK_GRAY
        border_w = max(1, s(2)) if hovered else 1
        pygame.draw.rect(surface, border_color, rect, border_w, border_radius=s(6))

        text_color = WHITE if hovered else GRAY
        text_surf = self.font_medium.render(label, True, text_color)
        text_rect = text_surf.get_rect(center=rect.center)
        surface.blit(text_surf, text_rect)

        if hovered:
            bracket_l = self.font_small.render(">>", True, accent_color)
            bracket_r = self.font_small.render("<<", True, accent_color)
            surface.blit(bracket_l, (rect.left + s(10),
                                     rect.centery - bracket_l.get_height() // 2))
            surface.blit(bracket_r, (rect.right - bracket_r.get_width() - s(10),
                                     rect.centery - bracket_r.get_height() // 2))

    def draw_pause_menu(self, surface):
        W, H = self.W, self.H
        overlay = pygame.Surface((W, H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        surface.blit(overlay, (0, 0))

        title = self.font_large.render("PAUSED", True, NEON_CYAN)
        title_rect = title.get_rect(center=(W // 2, H // 2 - self._s(30)))
        surface.blit(title, title_rect)

        hint = self.font_small.render("[ESC] Resume  |  [R] Restart  |  [Q] Quit", True, GRAY)
        hint_rect = hint.get_rect(center=(W // 2, H // 2 + self._s(30)))
        surface.blit(hint, hint_rect)

    def _draw_rounded_bar(self, surface, x, y, w, h, color):
        if w <= 0:
            return
        pygame.draw.rect(surface, color, (x, y, w, h), border_radius=max(1, self._s(3)))

    def _draw_scanlines(self, surface):
        W, H = self.W, self.H
        step = max(2, self._s(4))
        scanline_surf = pygame.Surface((W, max(1, self._s(2))), pygame.SRCALPHA)
        scanline_surf.fill((0, 0, 0, self.scanline_alpha))
        for y in range(0, H, step):
            surface.blit(scanline_surf, (0, y))

    def get_upgrade_click(self, mouse_pos):
        for rect, key in self.upgrade_rects:
            if rect.collidepoint(mouse_pos):
                return key
        return None
