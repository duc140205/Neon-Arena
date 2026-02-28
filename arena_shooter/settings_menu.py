"""
settings_menu.py - Full settings menu with keyboard/mouse navigation
Handles Display and Performance settings with visual selection UI.
"""

import pygame
import math
from .settings import (
    SCREEN_WIDTH, SCREEN_HEIGHT,
    NEON_CYAN, NEON_MAGENTA, NEON_PINK, NEON_YELLOW, NEON_GREEN,
    WHITE, GRAY, DARK_GRAY, DARK_BG,
)
from .config import RESOLUTION_OPTIONS, SCREEN_MODE_OPTIONS, FPS_OPTIONS, VOLUME_OPTIONS

# Must match Game._BGM_MASTER_SCALE in game.py so the live preview sounds
# identical to the in-game volume.
_BGM_MASTER_SCALE = 0.4


class SettingsMenu:
    """
    Interactive settings menu with categories, arrow-based option cycling,
    and keyboard/mouse navigation.
    """

    def __init__(self):
        pygame.font.init()
        self._last_scale = -1  # force initial font creation
        self._create_fonts(1.0)  # base fonts

        # Menu structure: list of (category, items)
        # Each item: (label, setting_key, get_value_fn, get_options_fn)
        self.items = [
            {"type": "heading", "label": "DISPLAY"},
            {
                "type": "option",
                "label": "Resolution",
                "key": "resolution",
            },
            {
                "type": "option",
                "label": "Screen Mode",
                "key": "screen_mode",
            },
            {"type": "separator"},
            {"type": "heading", "label": "PERFORMANCE"},
            {
                "type": "option",
                "label": "Frame Rate (FPS)",
                "key": "fps",
            },
            {
                "type": "option",
                "label": "VSync",
                "key": "vsync",
            },
            {"type": "separator"},
            {"type": "heading", "label": "AUDIO"},
            {
                "type": "option",
                "label": "Music Volume",
                "key": "music_volume",
            },
            {
                "type": "option",
                "label": "SFX Volume",
                "key": "sfx_volume",
            },
            {"type": "separator"},
            {"type": "button", "label": "Apply & Save", "action": "apply"},
            {"type": "button", "label": "Back", "action": "back"},
        ]

        self.selected_index = 1  # start on first option (skip heading)
        self.hover_index = -1
        self._item_rects = []  # for mouse hover detection

        # Temporary values (edited but not yet applied)
        self.temp_resolution_idx = 0
        self.temp_screen_mode_idx = 0
        self.temp_fps_idx = 1
        self.temp_vsync = False
        self.temp_music_vol_idx = 7   # default: 0.7
        self.temp_sfx_vol_idx   = 7   # default: 0.7

        # Animation
        self.anim_time = 0.0
        self.flash_timer = 0.0
        self.flash_message = ""
        # Maps item-index → x pixel that divides the < arrow from the > arrow.
        # Populated during draw; used by the mouse click handler.
        self._arrow_split_x: dict = {}

    def _create_fonts(self, sc):
        """Create fonts scaled for current resolution."""
        self._last_scale = sc
        def sz(base):
            return max(8, int(base * sc))
        try:
            self.font_title = pygame.font.SysFont("consolas", sz(48), bold=True)
            self.font_heading = pygame.font.SysFont("consolas", sz(24), bold=True)
            self.font_option = pygame.font.SysFont("consolas", sz(20))
            self.font_value = pygame.font.SysFont("consolas", sz(20), bold=True)
            self.font_hint = pygame.font.SysFont("consolas", sz(14))
        except Exception:
            self.font_title = pygame.font.Font(None, sz(48))
            self.font_heading = pygame.font.Font(None, sz(24))
            self.font_option = pygame.font.Font(None, sz(20))
            self.font_value = pygame.font.Font(None, sz(20))
            self.font_hint = pygame.font.Font(None, sz(14))

    def open(self, config):
        """Initialize temp values from current config."""
        self.temp_resolution_idx  = config.resolution_index
        self.temp_screen_mode_idx = config.screen_mode_index
        self.temp_fps_idx         = config.fps_index
        self.temp_vsync           = config.vsync
        self.temp_music_vol_idx   = config.music_volume_index
        self.temp_sfx_vol_idx     = config.sfx_volume_index
        self.selected_index = 1
        self.flash_timer = 0.0

    def _get_selectable_indices(self):
        """Return indices of items that can be selected."""
        return [
            i for i, item in enumerate(self.items)
            if item["type"] in ("option", "button")
        ]

    def _get_value_text(self, key):
        """Get the display text for a setting's current temp value."""
        if key == "resolution":
            res = RESOLUTION_OPTIONS[self.temp_resolution_idx]
            return f"{res[0]}x{res[1]}"
        elif key == "screen_mode":
            mode = SCREEN_MODE_OPTIONS[self.temp_screen_mode_idx]
            return mode.replace("_", " ").title()
        elif key == "fps":
            return str(FPS_OPTIONS[self.temp_fps_idx])
        elif key == "vsync":
            return "ON" if self.temp_vsync else "OFF"
        elif key == "music_volume":
            return f"{int(VOLUME_OPTIONS[self.temp_music_vol_idx] * 100)}%"
        elif key == "sfx_volume":
            return f"{int(VOLUME_OPTIONS[self.temp_sfx_vol_idx] * 100)}%"
        return ""

    def _cycle_value(self, key, direction):
        """Cycle a setting value left (-1) or right (+1)."""
        if key == "resolution":
            self.temp_resolution_idx = (
                (self.temp_resolution_idx + direction) % len(RESOLUTION_OPTIONS)
            )
        elif key == "screen_mode":
            self.temp_screen_mode_idx = (
                (self.temp_screen_mode_idx + direction) % len(SCREEN_MODE_OPTIONS)
            )
        elif key == "fps":
            self.temp_fps_idx = (
                (self.temp_fps_idx + direction) % len(FPS_OPTIONS)
            )
        elif key == "vsync":
            self.temp_vsync = not self.temp_vsync
        elif key == "music_volume":
            self.temp_music_vol_idx = (
                (self.temp_music_vol_idx + direction) % len(VOLUME_OPTIONS)
            )
            # Live preview: update BGM volume immediately so the user can
            # hear the change before clicking "Apply & Save".
            try:
                pygame.mixer.music.set_volume(
                    VOLUME_OPTIONS[self.temp_music_vol_idx] * _BGM_MASTER_SCALE
                )
            except Exception:
                pass
        elif key == "sfx_volume":
            self.temp_sfx_vol_idx = (
                (self.temp_sfx_vol_idx + direction) % len(VOLUME_OPTIONS)
            )

    def handle_event(self, event, config):
        """
        Handle input events for the settings menu.
        Returns:
            "back"  - user wants to go back
            "apply" - user applied settings (config is updated)
            None    - no action
        """
        selectable = self._get_selectable_indices()

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self._restore_music_volume(config)
                return "back"

            elif event.key in (pygame.K_UP, pygame.K_w):
                # Move selection up
                if self.selected_index in selectable:
                    pos = selectable.index(self.selected_index)
                    pos = (pos - 1) % len(selectable)
                    self.selected_index = selectable[pos]
                elif selectable:
                    self.selected_index = selectable[0]

            elif event.key in (pygame.K_DOWN, pygame.K_s):
                # Move selection down
                if self.selected_index in selectable:
                    pos = selectable.index(self.selected_index)
                    pos = (pos + 1) % len(selectable)
                    self.selected_index = selectable[pos]
                elif selectable:
                    self.selected_index = selectable[0]

            elif event.key in (pygame.K_LEFT, pygame.K_a):
                item = self.items[self.selected_index]
                if item["type"] == "option":
                    self._cycle_value(item["key"], -1)

            elif event.key in (pygame.K_RIGHT, pygame.K_d):
                item = self.items[self.selected_index]
                if item["type"] == "option":
                    self._cycle_value(item["key"], +1)

            elif event.key == pygame.K_RETURN:
                item = self.items[self.selected_index]
                if item["type"] == "button":
                    if item["action"] == "apply":
                        return self._apply_settings(config)
                    elif item["action"] == "back":
                        self._restore_music_volume(config)
                        return "back"
                elif item["type"] == "option":
                    # Enter on option cycles right
                    self._cycle_value(item["key"], +1)

        elif event.type == pygame.MOUSEMOTION:
            # Update hover
            mouse_pos = event.pos
            self.hover_index = -1
            for idx, rect in self._item_rects:
                if rect.collidepoint(mouse_pos):
                    if self.items[idx]["type"] in ("option", "button"):
                        self.hover_index = idx
                        self.selected_index = idx
                    break

        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                mouse_pos = event.pos
                for idx, rect in self._item_rects:
                    if rect.collidepoint(mouse_pos):
                        item = self.items[idx]
                        if item["type"] == "option":
                            # Use the stored arrow split so left/right clicks
                            # map correctly regardless of label width.
                            split_x = self._arrow_split_x.get(idx, rect.centerx)
                            if mouse_pos[0] < split_x:
                                self._cycle_value(item["key"], -1)
                            else:
                                self._cycle_value(item["key"], +1)
                        elif item["type"] == "button":
                            if item["action"] == "apply":
                                return self._apply_settings(config)
                            elif item["action"] == "back":
                                self._restore_music_volume(config)
                                return "back"
                        break

        return None

    def _apply_settings(self, config):
        """Apply temp values to config, save, and return 'apply'."""
        config.resolution    = list(RESOLUTION_OPTIONS[self.temp_resolution_idx])
        config.screen_mode   = SCREEN_MODE_OPTIONS[self.temp_screen_mode_idx]
        config.fps           = FPS_OPTIONS[self.temp_fps_idx]
        config.vsync         = self.temp_vsync
        config.music_volume  = VOLUME_OPTIONS[self.temp_music_vol_idx]
        config.sfx_volume    = VOLUME_OPTIONS[self.temp_sfx_vol_idx]
        config.save()
        self.flash_message = "Settings saved!"
        self.flash_timer = 1.5
        return "apply"

    def _restore_music_volume(self, config):
        """Restore BGM to the persisted config volume when the user cancels
        without saving (undoes any live preview changes)."""
        try:
            pygame.mixer.music.set_volume(config.music_volume * _BGM_MASTER_SCALE)
        except Exception:
            pass

    def draw(self, surface, time):
        """Draw the full settings menu at native resolution."""
        self.anim_time = time
        W, H = surface.get_size()
        sc = W / 1280  # scale relative to base

        # Rebuild fonts if resolution changed
        if abs(sc - self._last_scale) > 0.01:
            self._create_fonts(sc)

        # Helper for scaling base pixel values
        def si(v):
            return max(1, int(v * sc))

        # ── Background ──
        surface.fill(DARK_BG)

        # Subtle animated grid
        grid_step = max(4, si(80))
        for x in range(0, W, grid_step):
            alpha = int(12 + 6 * math.sin(time * 1.5 + x * 0.008))
            line_surf = pygame.Surface((1, H), pygame.SRCALPHA)
            line_surf.fill((0, 255, 255, alpha))
            surface.blit(line_surf, (x, 0))
        for y in range(0, H, grid_step):
            alpha = int(12 + 6 * math.sin(time * 1.5 + y * 0.008))
            line_surf = pygame.Surface((W, 1), pygame.SRCALPHA)
            line_surf.fill((255, 0, 200, alpha))
            surface.blit(line_surf, (0, y))

        # ── Title ──
        title = self.font_title.render("SETTINGS", True, NEON_CYAN)
        title_y = si(60)
        title_rect = title.get_rect(center=(W // 2, title_y))
        glow = self.font_title.render("SETTINGS", True, (*NEON_CYAN, 30))
        for dx, dy in [(2, 0), (-2, 0), (0, 2), (0, -2)]:
            surface.blit(glow, glow.get_rect(center=(W // 2 + dx, title_y + dy)))
        surface.blit(title, title_rect)

        # ── Decorative line ──
        line_y = si(95)
        pygame.draw.line(surface, NEON_CYAN, (W // 2 - si(200), line_y),
                         (W // 2 + si(200), line_y), 1)

        # ── Items ──
        self._item_rects = []
        current_y = si(110)          # tighter top margin to fit all items
        item_width = si(500)
        item_x = (W - item_width) // 2

        for i, item in enumerate(self.items):
            if item["type"] == "heading":
                current_y += si(6)
                self._draw_heading(surface, item["label"], item_x, current_y, item_width)
                current_y += si(28)  # was 38

            elif item["type"] == "separator":
                current_y += si(4)   # was 8
                sep_surf = pygame.Surface((item_width, 1), pygame.SRCALPHA)
                sep_surf.fill((*NEON_CYAN, 30))
                surface.blit(sep_surf, (item_x, current_y))
                current_y += si(8)   # was 12

            elif item["type"] == "option":
                rect = pygame.Rect(item_x, current_y, item_width, si(40))  # was 44
                self._item_rects.append((i, rect))
                is_selected = (i == self.selected_index)
                value_text = self._get_value_text(item["key"])
                self._draw_option_row(surface, item["label"], value_text,
                                      rect, is_selected, time, item_idx=i)
                current_y += si(44)  # was 52

            elif item["type"] == "button":
                btn_inset = si(100)
                rect = pygame.Rect(item_x + btn_inset, current_y,
                                   item_width - btn_inset * 2, si(40))  # was 44
                self._item_rects.append((i, rect))
                is_selected = (i == self.selected_index)
                is_apply = (item["action"] == "apply")
                self._draw_button(surface, item["label"], rect, is_selected,
                                  is_apply, time)
                current_y += si(46)  # was 56

        # ── Hints ──
        hints_y = H - si(45)
        hint_lines = [
            "[↑↓] Navigate   [←→] Change   [Enter] Select   [ESC] Back",
        ]
        for line in hint_lines:
            hint_surf = self.font_hint.render(line, True, GRAY)
            hint_rect = hint_surf.get_rect(center=(W // 2, hints_y))
            surface.blit(hint_surf, hint_rect)
            hints_y += si(18)

        # ── Flash message ──
        if self.flash_timer > 0:
            alpha = min(255, int(self.flash_timer * 255))
            flash_surf = self.font_heading.render(self.flash_message, True, NEON_GREEN)
            flash_surf.set_alpha(alpha)
            flash_rect = flash_surf.get_rect(center=(W // 2, H - si(80)))
            surface.blit(flash_surf, flash_rect)

    def update(self, dt):
        """Update animation timers."""
        self.flash_timer = max(0, self.flash_timer - dt)

    def _draw_heading(self, surface, label, x, y, width):
        """Draw a category heading."""
        # Small colored marker
        marker_color = NEON_MAGENTA
        pygame.draw.rect(surface, marker_color, (x, y + 4, 4, 18))
        text = self.font_heading.render(label, True, NEON_MAGENTA)
        surface.blit(text, (x + 14, y + 2))

    def _draw_option_row(self, surface, label, value, rect, selected, time, item_idx=None):
        """Draw a single option row with label, value, and arrows."""
        # Background
        if selected:
            bg_alpha = 40 + int(15 * math.sin(time * 4))
            bg_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            bg_surf.fill((0, 255, 255, bg_alpha))
            surface.blit(bg_surf, rect.topleft)
            # Left border accent
            pygame.draw.line(surface, NEON_CYAN,
                             (rect.left, rect.top), (rect.left, rect.bottom), 3)

        # Option border (subtle)
        border_color = NEON_CYAN if selected else (40, 40, 70)
        pygame.draw.rect(surface, border_color, rect, 1, border_radius=4)

        # Label (left side)
        label_color = WHITE if selected else GRAY
        label_surf = self.font_option.render(label, True, label_color)
        surface.blit(label_surf, (rect.left + 16, rect.centery - label_surf.get_height() // 2))

        # Value with arrows (right side)
        value_color = NEON_YELLOW if selected else NEON_CYAN
        value_surf = self.font_value.render(value, True, value_color)

        # Arrow characters
        arrow_color = NEON_CYAN if selected else DARK_GRAY
        left_arrow = self.font_value.render("<", True, arrow_color)
        right_arrow = self.font_value.render(">", True, arrow_color)

        # Position: [< value >] aligned to right of rect
        value_total_w = (left_arrow.get_width() + 10 +
                         value_surf.get_width() + 10 +
                         right_arrow.get_width())
        vx = rect.right - value_total_w - 16

        # Store the split x so the mouse handler can tell < from >.
        # Split is the midpoint between the two arrows: right edge of < plus
        # half the gap + value width + half the gap before >.
        # Anything to the LEFT of split_x → decrease; RIGHT → increase.
        if item_idx is not None:
            self._arrow_split_x[item_idx] = vx + left_arrow.get_width() + 5 + value_surf.get_width() // 2

        cy = rect.centery
        surface.blit(left_arrow, (vx, cy - left_arrow.get_height() // 2))
        vx += left_arrow.get_width() + 10
        surface.blit(value_surf, (vx, cy - value_surf.get_height() // 2))
        vx += value_surf.get_width() + 10
        surface.blit(right_arrow, (vx, cy - right_arrow.get_height() // 2))

    def _draw_button(self, surface, label, rect, selected, is_primary, time):
        """Draw a button."""
        if is_primary:
            base_color = NEON_GREEN
        else:
            base_color = GRAY

        if selected:
            # Highlighted background
            pulse = int(20 * math.sin(time * 5))
            bg_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            if is_primary:
                bg_surf.fill((*NEON_GREEN, 40 + pulse))
            else:
                bg_surf.fill((100, 100, 120, 30 + pulse))
            surface.blit(bg_surf, rect.topleft)
            border_color = base_color
            border_w = 2
        else:
            border_color = DARK_GRAY
            border_w = 1

        pygame.draw.rect(surface, border_color, rect, border_w, border_radius=6)

        text_color = WHITE if selected else GRAY
        text_surf = self.font_option.render(label, True, text_color)
        text_rect = text_surf.get_rect(center=rect.center)
        surface.blit(text_surf, text_rect)

        # Bracket decoration for selected buttons
        if selected:
            bracket_l = self.font_option.render(">>", True, base_color)
            bracket_r = self.font_option.render("<<", True, base_color)
            surface.blit(bracket_l, (rect.left + 8, rect.centery - bracket_l.get_height() // 2))
            surface.blit(bracket_r, (rect.right - bracket_r.get_width() - 8,
                                     rect.centery - bracket_r.get_height() // 2))
