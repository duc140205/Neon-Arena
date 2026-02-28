"""
game.py - Game state machine and main game loop logic
Renders at native resolution using camera.s() scaling.
No logical surface — the game surface IS the display at full resolution.
"""

import pygame
import math
import random
import os
from .settings import (
    SCREEN_WIDTH, SCREEN_HEIGHT, FPS, TITLE,
    ARENA_WIDTH, ARENA_HEIGHT, GRID_SIZE,
    BLACK, DARK_BG, GRID_COLOR,
    NEON_CYAN, NEON_MAGENTA, NEON_PINK, NEON_YELLOW, NEON_ORANGE, NEON_GREEN,
    UPGRADES,
    SHOCKWAVE_RADIUS, SHOCKWAVE_PUSHBACK,
    REFLEX_DURATION,
    SPEED_BOOST_MULT,
    BOSS_SLAM_DAMAGE,
    SLIME_BOSS_SHOCKWAVE_DAMAGE,
)
from .obstacles import generate_obstacles, PowerUpManager
from .config import Config, resource_path, assets
from .player import Player
from .particles import ParticleSystem
from .camera import Camera
from .enemy_manager import EnemyManager
from .ui import UI
from .settings_menu import SettingsMenu


class GameState:
    MENU = "menu"
    PLAYING = "playing"
    UPGRADE = "upgrade"
    PAUSED = "paused"
    GAME_OVER = "game_over"
    SETTINGS = "settings"


class Game:
    """Main game class — renders directly at native resolution."""

    def __init__(self):
        # Centre the window before SDL creates it (checked at set_mode time).
        # Must be set before pygame.init() to cover the initial window.
        os.environ['SDL_VIDEO_CENTERED'] = '1'
        os.environ.pop('SDL_VIDEO_WINDOW_POS', None)
        # Prevent SDL from minimising (and potentially crashing) the window
        # when it loses focus — critical for Win+Shift+S screenshot overlay.
        os.environ['SDL_VIDEO_MINIMIZE_ON_FOCUS_LOSS'] = '0'

        pygame.init()
        pygame.mixer.init()

        # ── Config ───────────────────────────────────────
        self.config = Config()

        # ── Display ──────────────────────────────────────
        self.screen = None
        self.actual_width = SCREEN_WIDTH
        self.actual_height = SCREEN_HEIGHT
        self._apply_display_mode()

        pygame.display.set_caption(TITLE)

        # ── Window / Taskbar Icon ────────────────────────
        try:
            icon_path = assets.icon("neonarena.ico")
            if os.path.exists(icon_path):
                icon_surface = pygame.image.load(icon_path)
                pygame.display.set_icon(icon_surface)
        except Exception:
            pass  # No icon available — not fatal
        self.clock = pygame.time.Clock()
        self.running = True
        self.state = GameState.MENU
        self.time = 0.0
        self.fps = 60.0

        # ── Systems ──────────────────────────────────────
        self.particles = ParticleSystem()
        # Camera sized to actual display for native rendering
        self.camera = Camera(self.actual_width, self.actual_height)
        self.ui = UI(self.actual_width, self.actual_height)
        self.enemy_manager = EnemyManager()
        self.settings_menu = SettingsMenu()

        # Vignette (at actual resolution)
        self._vignette_surface = self._create_vignette()

        # Sprite groups
        self.player = None
        self.enemies = pygame.sprite.Group()
        self.player_bullets = pygame.sprite.Group()
        self.enemy_bullets = pygame.sprite.Group()

        # World objects
        self.obstacles = []
        self.powerup_manager = None
        self.ghost_trails = []  # [(x, y, lifetime, damage, radius)]
        self.toxic_pools = []   # [(x, y, lifetime, damage, radius)] for SlimeBoss

        # Upgrade state
        self.upgrade_options = []
        self.pending_levelups = 0

        self._pre_settings_state = GameState.MENU

        # Sound
        self._init_sounds()

    # ── Display Mode Management ──────────────────────────

    def _apply_display_mode(self):
        """Apply display settings — fully reliable windowed / fullscreen switch."""
        w = self.config.display_width
        h = self.config.display_height
        mode = self.config.screen_mode

        # ── Step 1: Capture desktop geometry BEFORE tearing down the display.
        # pygame.display.Info() returns garbage after display.quit().
        try:
            info = pygame.display.Info()
            desktop_w = info.current_w
            desktop_h = info.current_h
        except Exception:
            desktop_w, desktop_h = 1920, 1080  # safe fallback

        # ── Step 2: Set env vars BEFORE the display is recreated.
        # SDL reads these at SDL_CreateWindow time.
        if mode == "windowed":
            os.environ['SDL_VIDEO_CENTERED'] = '1'
            os.environ.pop('SDL_VIDEO_WINDOW_POS', None)
            # Prevent SDL from auto-scaling the surface on HiDPI displays.
            os.environ['SDL_VIDEO_HIGHDPI_DISABLED'] = '1'
            # Clamp to logical desktop so the window never overflows.
            if desktop_w > 0 and desktop_h > 0:
                w = min(w, desktop_w)
                h = min(h, desktop_h)
            # ── Safety offset ──────────────────────────────────────────────
            # When the requested resolution exactly matches the desktop size,
            # Windows/SDL interprets a RESIZABLE window that fills the entire
            # screen as borderless-fullscreen and forces it to stay that way.
            # Subtracting a few pixels (2px width, 40px for the title bar)
            # forces the OS to create a genuine decorated window.
            if desktop_w > 0 and desktop_h > 0 and w == desktop_w and h == desktop_h:
                w = max(640, w - 2)
                h = max(480, h - 40)
        else:  # fullscreen — SDL manages everything
            os.environ.pop('SDL_VIDEO_CENTERED', None)
            os.environ.pop('SDL_VIDEO_WINDOW_POS', None)
            os.environ.pop('SDL_VIDEO_HIGHDPI_DISABLED', None)

        # ── Step 3: Full display-subsystem teardown.
        # The only reliable way to clear OS-level window styles (WS_POPUP for
        # fullscreen, WS_THICKFRAME for resizable, etc.) on Windows.
        try:
            pygame.display.quit()
            pygame.display.init()
        except Exception:
            pass

        # ── Step 4: Buffer reset — create a tiny plain window AFTER teardown.
        # Transitioning directly from "no window" → FULLSCREEN or RESIZABLE can
        # leave stale driver state on some Windows/SDL2 combos.  A neutral
        # 100×100 window anchors the plain windowed state first.
        try:
            pygame.display.set_mode((100, 100), 0)
        except Exception:
            pass

        # ── Step 5: Re-assert centering immediately before the real set_mode.
        # display.init() can internally reset SDL's hint cache on some drivers.
        if mode == "windowed":
            os.environ['SDL_VIDEO_CENTERED'] = '1'

        # ── Step 6: Choose flags and create the final window.
        if mode == "fullscreen":
            flags = pygame.FULLSCREEN | pygame.HWSURFACE | pygame.DOUBLEBUF
        else:
            # pygame.SHOWN makes the window visible immediately without any
            # compositor hide/show flicker.  RESIZABLE only — no FULLSCREEN,
            # no NOFRAME, no other flags that could confuse the WM.
            flags = pygame.SHOWN | pygame.RESIZABLE

        print(f"[Display] Applying mode={mode!r} | target={w}x{h} | "
              f"desktop={desktop_w}x{desktop_h} | flags={flags:#010x}")
        self.screen = self._safe_set_mode((w, h), flags)

        # ── Step 7: Read back the ACTUAL surface size.
        self.actual_width, self.actual_height = self.screen.get_size()
        scale = self.actual_width / 1280
        print(f"[Display] Result: actual={self.actual_width}x{self.actual_height}, "
              f"scale={scale:.2f}x")
        pygame.display.set_caption(TITLE)

        # Force the OS / compositor to acknowledge the new window state.
        pygame.display.flip()

    def _safe_set_mode(self, size, flags):
        vsync_flag = 1 if self.config.vsync else 0
        try:
            return pygame.display.set_mode(size, flags, vsync=vsync_flag)
        except TypeError:
            return pygame.display.set_mode(size, flags)

    def _on_resolution_changed(self):
        """Rebuild resolution-dependent resources after a mode change."""
        self.camera.resize(self.actual_width, self.actual_height)
        self.ui = UI(self.actual_width, self.actual_height)
        self._vignette_surface = self._create_vignette()

    # ── Sound System ─────────────────────────────────────

    def _init_sounds(self):
        self.sounds = {}
        try:
            sample_rate = 44100
            shoot_arr = pygame.sndarray.make_sound(
                self._generate_beep(440, 0.05, sample_rate)
            )
            self.sounds["shoot"] = shoot_arr
            self.sounds["shoot"].set_volume(0.15)
        except Exception:
            pass
        try:
            sample_rate = 44100
            explode_arr = pygame.sndarray.make_sound(
                self._generate_noise(0.1, sample_rate)
            )
            self.sounds["explode"] = explode_arr
            self.sounds["explode"].set_volume(0.2)
        except Exception:
            pass
        try:
            sample_rate = 44100
            levelup_arr = pygame.sndarray.make_sound(
                self._generate_beep(880, 0.15, sample_rate)
            )
            self.sounds["levelup"] = levelup_arr
            self.sounds["levelup"].set_volume(0.25)
        except Exception:
            pass

    def _generate_beep(self, freq, duration, sample_rate=44100):
        import numpy as np
        t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
        wave = (np.sin(2 * np.pi * freq * t) * 16000).astype(np.int16)
        fade = np.linspace(1, 0, len(wave))
        wave = (wave * fade).astype(np.int16)
        return np.column_stack((wave, wave))

    def _generate_noise(self, duration, sample_rate=44100):
        import numpy as np
        samples = int(sample_rate * duration)
        noise = (np.random.randint(-8000, 8000, samples)).astype(np.int16)
        fade = np.linspace(1, 0, samples)
        noise = (noise * fade).astype(np.int16)
        return np.column_stack((noise, noise))

    def _play_sound(self, name):
        if name in self.sounds:
            try:
                self.sounds[name].play()
            except Exception:
                pass

    # ── Background ───────────────────────────────────────

    def _draw_background(self, surface):
        """Draw arena background with cyberpunk grid, at native resolution."""
        surface.fill(DARK_BG)
        sc = self.camera.s

        cam_x = int(self.camera.x)
        cam_y = int(self.camera.y)

        # Grid lines (scaled to native resolution)
        start_x = int(-(cam_x % GRID_SIZE) * self.camera.scale)
        step = sc(GRID_SIZE)
        if step < 2:
            step = 2
        sw, sh = surface.get_size()

        x = start_x
        grid_idx = int(-cam_x // GRID_SIZE)
        while x < sw + step:
            if grid_idx % 4 == 0:
                color = (30, 30, 70)
            else:
                color = GRID_COLOR
            pygame.draw.line(surface, color, (x, 0), (x, sh))
            x += step
            grid_idx += 1

        start_y = int(-(cam_y % GRID_SIZE) * self.camera.scale)
        y = start_y
        grid_idy = int(-cam_y // GRID_SIZE)
        while y < sh + step:
            if grid_idy % 4 == 0:
                color = (30, 30, 70)
            else:
                color = GRID_COLOR
            pygame.draw.line(surface, color, (0, y), (sw, y))
            y += step
            grid_idy += 1

        # Arena border
        border_rect = self.camera.apply_rect(
            pygame.Rect(0, 0, ARENA_WIDTH, ARENA_HEIGHT)
        )
        pygame.draw.rect(surface, NEON_CYAN, border_rect, max(1, sc(2)))

        # Vignette
        surface.blit(self._vignette_surface, (0, 0))

    def _create_vignette(self):
        """Create vignette at actual display resolution."""
        w, h = self.actual_width, self.actual_height
        vignette = pygame.Surface((w, h), pygame.SRCALPHA)
        edge_h = max(20, h // 18)
        for i in range(edge_h):
            alpha = int(60 * (1 - i / edge_h))
            line_surf = pygame.Surface((w, 1), pygame.SRCALPHA)
            line_surf.fill((0, 0, 10, alpha))
            vignette.blit(line_surf, (0, i))
            vignette.blit(line_surf, (0, h - 1 - i))
        return vignette

    # ── Game State Management ────────────────────────────

    def new_game(self):
        self.particles = ParticleSystem()
        self.camera = Camera(self.actual_width, self.actual_height)
        self.enemy_manager = EnemyManager()
        self.enemies.empty()
        self.player_bullets.empty()
        self.enemy_bullets.empty()
        self.player = Player(ARENA_WIDTH / 2, ARENA_HEIGHT / 2, self.particles)
        self.obstacles = generate_obstacles()
        self.powerup_manager = PowerUpManager(self.obstacles, self.particles)
        self.ghost_trails = []
        self.toxic_pools = []
        self.upgrade_options = []
        self.pending_levelups = 0
        self.state = GameState.PLAYING

    def _open_settings(self):
        self._pre_settings_state = self.state
        self.settings_menu.open(self.config)
        self.state = GameState.SETTINGS

    def _close_settings(self):
        self.state = self._pre_settings_state

    # ── Main Loop ────────────────────────────────────────

    def run(self):
        while self.running:
            # Always tick the clock and pump events, even when unfocused, so
            # the OS window message loop stays alive (avoids "not responding").
            dt = min(self.clock.tick(self.config.fps) / 1000.0, 0.033)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    return
                self._handle_event(event)

            if pygame.display.get_active():
                # ── Normal active frame ──────────────────────────────────────
                self.time += dt
                self.fps = self.clock.get_fps()
                self._update(dt)
                self._draw(self.screen)
                pygame.display.flip()
            else:
                # ── Safe-sleep: window obscured / focus stolen ───────────────
                # Drop to ~10 FPS, keep pumping so the window stays responsive,
                # and skip all logic + drawing to prevent a crash while the
                # Win+Shift+S screenshot overlay (or any other overlay) is open.
                if self.player is not None:
                    self.player.is_shooting = False
                pygame.time.delay(100)   # ~10 FPS
                pygame.event.pump()      # keep OS message loop alive
                continue

        pygame.quit()

    # ── Event Handling ───────────────────────────────────

    def _handle_event(self, event):
        # ── Focus / visibility events ───────────────────────────────────────
        # Covers pygame 1.x ACTIVEEVENT, SDL2 WINDOWFOCUSLOST, and the newer
        # WINDOWLOSTFOCUS constant — whichever the installed SDL version fires.
        if event.type in (pygame.ACTIVEEVENT,
                          pygame.WINDOWFOCUSLOST,
                          getattr(pygame, 'WINDOWLOSTFOCUS', -1)):
            focus_lost = (
                (event.type == pygame.ACTIVEEVENT and getattr(event, 'gain', 1) == 0)
                or event.type != pygame.ACTIVEEVENT
            )
            if focus_lost:
                # Stop shooting immediately — the safe-sleep branch in run()
                # will also enforce this every frame while unfocused.
                if self.player is not None:
                    self.player.is_shooting = False
                # Flush stuck mouse-button signals from the event queue.
                pygame.event.clear(pygame.MOUSEBUTTONDOWN)
                pygame.event.clear(pygame.MOUSEBUTTONUP)
                # Give the OS snipping tool a clean, visible cursor.
                pygame.mouse.set_visible(True)
            return

        # Handle window resize
        if event.type == pygame.VIDEORESIZE:
            self.actual_width, self.actual_height = event.w, event.h
            self.screen = self._safe_set_mode((event.w, event.h), pygame.RESIZABLE)
            self._on_resolution_changed()
            return

        # Settings menu — pass native events directly (rects are at native resolution)
        if self.state == GameState.SETTINGS:
            result = self.settings_menu.handle_event(event, self.config)
            if result == "back":
                self._close_settings()
            elif result == "apply":
                self._apply_display_mode()
                self._on_resolution_changed()
                pygame.event.clear()  # discard stale resize/activate events
            return

        if event.type == pygame.KEYDOWN:
            if self.state == GameState.MENU:
                if event.key == pygame.K_RETURN:
                    self.new_game()
                elif event.key == pygame.K_ESCAPE:
                    self.running = False
            elif self.state == GameState.PLAYING:
                if event.key == pygame.K_ESCAPE:
                    self.state = GameState.PAUSED
            elif self.state == GameState.PAUSED:
                if event.key == pygame.K_ESCAPE:
                    self.state = GameState.PLAYING
                elif event.key == pygame.K_r:
                    self.new_game()
                elif event.key == pygame.K_q:
                    self.state = GameState.MENU
            elif self.state == GameState.GAME_OVER:
                if event.key == pygame.K_r:
                    self.new_game()
                elif event.key == pygame.K_ESCAPE:
                    self.state = GameState.MENU

        elif event.type == pygame.MOUSEBUTTONDOWN:
            # Mouse pos is already in native pixels — use as-is for UI
            # but scale to logical (1280x720) for settings_menu / ui hit-testing
            logical_pos = self._to_logical(event.pos)

            if self.state == GameState.MENU:
                if event.button == 1:
                    if hasattr(self.ui, 'menu_start_rect') and self.ui.menu_start_rect.collidepoint(event.pos):
                        self.new_game()
                    elif hasattr(self.ui, 'menu_settings_rect') and self.ui.menu_settings_rect.collidepoint(event.pos):
                        self._open_settings()
                    elif hasattr(self.ui, 'menu_quit_rect') and self.ui.menu_quit_rect.collidepoint(event.pos):
                        self.running = False

            elif self.state == GameState.UPGRADE:
                if event.button == 1:
                    choice = self.ui.get_upgrade_click(event.pos)
                    if choice:
                        self.player.apply_upgrade(choice)
                        self._play_sound("levelup")
                        self.pending_levelups -= 1
                        if self.pending_levelups > 0:
                            self._generate_upgrade_options()
                        else:
                            self.state = GameState.PLAYING

    def _to_logical(self, pos):
        """Convert native screen pos to logical 1280x720 coordinates."""
        lx = pos[0] * SCREEN_WIDTH / self.actual_width
        ly = pos[1] * SCREEN_HEIGHT / self.actual_height
        return (int(lx), int(ly))

    def _make_logical_event(self, event):
        """Wrap a mouse event with logical-coordinate pos (for settings menu)."""
        logical_pos = self._to_logical(event.pos)

        class LogicalEvent:
            pass

        le = LogicalEvent()
        le.type = event.type
        le.pos = logical_pos
        if hasattr(event, 'button'):
            le.button = event.button
        if hasattr(event, 'buttons'):
            le.buttons = event.buttons
        if hasattr(event, 'rel'):
            le.rel = event.rel
        if hasattr(event, 'key'):
            le.key = event.key
        return le

    # ── Upgrade Generation ───────────────────────────────

    def _generate_upgrade_options(self):
        available = []
        for key, data in UPGRADES.items():
            if self.player.upgrade_levels.get(key, 0) < data["max_level"]:
                available.append(key)
        if not available:
            self.state = GameState.PLAYING
            return
        count = min(3, len(available))
        self.upgrade_options = random.sample(available, count)

    # ── Update ───────────────────────────────────────────

    def _update(self, dt):
        if self.state == GameState.PLAYING:
            self._update_playing(dt)
        elif self.state == GameState.SETTINGS:
            self.settings_menu.update(dt)

    def _update_playing(self, dt):
        # Mouse is in native screen pixels — pass directly
        mouse_pos = pygame.mouse.get_pos()

        self.player.update(dt, mouse_pos, self.camera)

        # Speed boost powerup
        saved_speed = self.player.speed
        if self.player.speed_boost_timer > 0:
            self.player.speed = saved_speed * SPEED_BOOST_MULT

        if self.player.try_shoot(self.player_bullets):
            self._play_sound("shoot")

        # Restore speed after shooting calc (it's used live during update)
        if self.player.speed_boost_timer > 0:
            self.player.speed = saved_speed

        self.camera.update(self.player.pos_x, self.player.pos_y, dt)

        self.enemy_manager.update(
            dt, self.enemies,
            self.player.pos_x, self.player.pos_y,
            self.camera.rect,
        )

        for enemy in self.enemies:
            enemy.update(dt, self.player.pos_x, self.player.pos_y, self.enemy_bullets)

        for bullet in self.player_bullets:
            bullet.update(dt)
        for bullet in self.enemy_bullets:
            bullet.update(dt)

        # ── Obstacle collision (player) ──
        for obs in self.obstacles:
            px, py = obs.push_circle_out(
                self.player.pos_x, self.player.pos_y, self.player.radius)
            self.player.pos_x = px
            self.player.pos_y = py

        # ── Obstacle collision (enemies) ──
        for enemy in self.enemies:
            for obs in self.obstacles:
                ex, ey = obs.push_circle_out(enemy.pos_x, enemy.pos_y, enemy.radius)
                enemy.pos_x = ex
                enemy.pos_y = ey

        # ── Obstacle collision (bullets) ──
        for bullet in list(self.player_bullets):
            for obs in self.obstacles:
                if obs.collides_circle(bullet.pos_x, bullet.pos_y, bullet.radius):
                    bullet.kill()
                    break
        for bullet in list(self.enemy_bullets):
            for obs in self.obstacles:
                if obs.collides_circle(bullet.pos_x, bullet.pos_y, bullet.radius):
                    bullet.kill()
                    break

        # ── Power-ups ──
        if self.powerup_manager:
            collected = self.powerup_manager.update(
                dt, self.player.pos_x, self.player.pos_y, self.player.radius)
            for pu_type, pu_color in collected:
                self.player.apply_powerup(pu_type)
                self._play_sound("levelup")

        # ── Speed Buff: digital dust trail ──
        if self.player.speed_boost_timer > 0 and not self.player.is_dashing:
            keys = pygame.key.get_pressed()
            moving = any([
                keys[pygame.K_w], keys[pygame.K_s],
                keys[pygame.K_a], keys[pygame.K_d],
                keys[pygame.K_UP], keys[pygame.K_DOWN],
                keys[pygame.K_LEFT], keys[pygame.K_RIGHT],
            ])
            if moving:
                self.particles.emit_speed_trail(
                    self.player.pos_x, self.player.pos_y,
                    self.player.aim_angle)

        # ── Damage Buff: barrel sparks ──
        if self.player.double_damage_timer > 0 and not self.player.is_dashing:
            gun_dist = self.player.radius + 10
            tip_x = self.player.pos_x + math.cos(self.player.aim_angle) * gun_dist
            tip_y = self.player.pos_y + math.sin(self.player.aim_angle) * gun_dist
            if random.random() < 0.4:  # don't spam every frame
                self.particles.emit_barrel_sparks(
                    tip_x, tip_y, self.player.aim_angle)

        # ── Ghost Trail damage ──
        # Merge player's trail positions into game's active trails
        if self.player.ghost_trail_positions:
            self.ghost_trails.extend(self.player.ghost_trail_positions)
            self.player.ghost_trail_positions.clear()

        # Update and apply ghost trail damage
        new_trails = []
        for tx, ty, tlife, tdmg, tradius in self.ghost_trails:
            tlife -= dt
            if tlife > 0:
                new_trails.append((tx, ty, tlife, tdmg, tradius))
                # Damage enemies touching the trail
                for enemy in list(self.enemies):
                    edx = enemy.pos_x - tx
                    edy = enemy.pos_y - ty
                    edist = math.sqrt(edx * edx + edy * edy)
                    if edist < tradius + enemy.radius:
                        enemy.take_damage(tdmg * dt, self.particles)
        self.ghost_trails = new_trails

        # ── SlimeBoss Toxic Pool handling ──
        # Collect toxic pools from any active SlimeBoss
        boss = self.enemy_manager.active_boss
        if boss and hasattr(boss, 'toxic_pools') and boss.toxic_pools:
            self.toxic_pools.extend(boss.toxic_pools)
            boss.toxic_pools.clear()

        # Update toxic pools and damage player
        new_toxic = []
        for tx, ty, tlife, tdmg, tradius in self.toxic_pools:
            tlife -= dt
            if tlife > 0:
                new_toxic.append((tx, ty, tlife, tdmg, tradius))
                # Damage player if touching the pool
                pdx = self.player.pos_x - tx
                pdy = self.player.pos_y - ty
                pdist = math.sqrt(pdx * pdx + pdy * pdy)
                if pdist < tradius + self.player.radius:
                    self.player.take_damage(tdmg)
        self.toxic_pools = new_toxic

        # ── Dash-end effects ──
        if self.player.dash_ended_this_frame:
            px = self.player.dash_end_x
            py = self.player.dash_end_y

            # Shockwave
            sw_level = self.player.upgrade_levels.get("dash_shockwave", 0)
            if sw_level > 0:
                radius = SHOCKWAVE_RADIUS + 30 * (sw_level - 1)
                pushback = SHOCKWAVE_PUSHBACK * (1.0 + 0.3 * (sw_level - 1))
                # Push enemies + damage them
                for enemy in self.enemies:
                    edx = enemy.pos_x - px
                    edy = enemy.pos_y - py
                    edist = math.sqrt(edx * edx + edy * edy)
                    if edist < radius and edist > 0:
                        nx = edx / edist
                        ny = edy / edist
                        enemy.pos_x += nx * pushback * 0.1
                        enemy.pos_y += ny * pushback * 0.1
                        enemy.take_damage(10 * sw_level, self.particles)
                # Destroy nearby enemy bullets
                for bullet in list(self.enemy_bullets):
                    bdx = bullet.pos_x - px
                    bdy = bullet.pos_y - py
                    if math.sqrt(bdx * bdx + bdy * bdy) < radius:
                        bullet.kill()
                # Visual: particle ring
                for i in range(24):
                    angle = i * math.pi * 2 / 24
                    ex = px + math.cos(angle) * radius * 0.5
                    ey = py + math.sin(angle) * radius * 0.5
                    self.particles.emit(ex, ey, NEON_MAGENTA, count=2,
                                        speed_range=(80, 200),
                                        lifetime_range=(0.2, 0.5),
                                        size_range=(3, 7))
                self._play_sound("explode")

            # Reflex Dash: check if bullets were phased through
            rx_level = self.player.upgrade_levels.get("reflex_dash", 0)
            if rx_level > 0 and self.player.bullets_phased > 0:
                self.player.reflex_timer = REFLEX_DURATION * (1.0 + 0.3 * (rx_level - 1))
                self.particles.emit(px, py, (220, 230, 255), count=15,
                                    speed_range=(60, 180),
                                    lifetime_range=(0.3, 0.6))
                self.player.bullets_phased = 0

        # ── Reflex Dash: count bullets overlapping during dash ──
        if self.player.is_dashing and self.player.upgrade_levels.get("reflex_dash", 0) > 0:
            for bullet in list(self.enemy_bullets):
                bdx = bullet.pos_x - self.player.pos_x
                bdy = bullet.pos_y - self.player.pos_y
                bdist = math.sqrt(bdx * bdx + bdy * bdy)
                if bdist < bullet.radius + self.player.radius:
                    self.player.bullets_phased += 1
                    bullet.kill()  # consume the bullet

        self.particles.update(dt)
        self._check_collisions()

        if not self.player.alive:
            self.state = GameState.GAME_OVER
            self.particles.emit_explosion(self.player.pos_x, self.player.pos_y, count=30)
            self._play_sound("explode")

    # ── Collisions ───────────────────────────────────────

    def _check_collisions(self):
        for bullet in list(self.player_bullets):
            for enemy in list(self.enemies):
                dx = bullet.pos_x - enemy.pos_x
                dy = bullet.pos_y - enemy.pos_y
                dist = math.sqrt(dx * dx + dy * dy)
                if dist < bullet.radius + enemy.radius:
                    killed = enemy.take_damage(bullet.damage, self.particles)
                    bullet.kill()
                    if killed:
                        self._play_sound("explode")
                        self.enemy_manager.on_enemy_killed()
                        leveled = self.player.gain_xp(enemy.xp_value)
                        if leveled:
                            self.pending_levelups += 1
                            self._generate_upgrade_options()
                            self.state = GameState.UPGRADE
                            # Scale difficulty with player level
                            self.enemy_manager.set_difficulty(self.player.level)
                    break

        if not self.player.is_dashing:
            for bullet in list(self.enemy_bullets):
                dx = bullet.pos_x - self.player.pos_x
                dy = bullet.pos_y - self.player.pos_y
                dist = math.sqrt(dx * dx + dy * dy)
                if dist < bullet.radius + self.player.radius:
                    self.player.take_damage(bullet.damage)
                    bullet.kill()

        if not self.player.is_dashing:
            for enemy in self.enemies:
                dx = enemy.pos_x - self.player.pos_x
                dy = enemy.pos_y - self.player.pos_y
                dist = math.sqrt(dx * dx + dy * dy)
                if dist < enemy.radius + self.player.radius:
                    self.player.take_damage(enemy.damage)

        # Boss slam damage (works for Boss, SniperBoss, SlimeBoss)
        for enemy in self.enemies:
            if hasattr(enemy, 'is_boss') and enemy.is_boss and enemy.slam_hit_player:
                # Use SlimeBoss-specific shockwave damage if applicable
                from .enemies import SlimeBoss as _SlimeBoss
                if isinstance(enemy, _SlimeBoss):
                    slam_dmg = SLIME_BOSS_SHOCKWAVE_DAMAGE
                else:
                    slam_dmg = BOSS_SLAM_DAMAGE
                self.player.take_damage(slam_dmg)
                self.particles.emit_explosion(
                    self.player.pos_x, self.player.pos_y,
                    color=NEON_YELLOW, count=20)
                self._play_sound("explode")

    # ── Drawing ──────────────────────────────────────────

    def _draw(self, surface):
        if self.state == GameState.MENU:
            self.ui.draw_main_menu(surface, self.time)
            return

        if self.state == GameState.SETTINGS:
            self.settings_menu.draw(surface, self.time)
            return

        if self.state in (GameState.PLAYING, GameState.PAUSED,
                          GameState.UPGRADE, GameState.GAME_OVER):
            self._draw_background(surface)

            # Obstacles
            for obs in self.obstacles:
                obs.draw(surface, self.camera)

            # Ghost trail fire zones
            for tx, ty, tlife, tdmg, tradius in self.ghost_trails:
                tsx, tsy = self.camera.apply(tx, ty)
                tr = self.camera.s(tradius)
                alpha = min(180, int(180 * (tlife / 0.8)))
                if tr > 0 and alpha > 0:
                    trail_surf = pygame.Surface((tr * 2, tr * 2), pygame.SRCALPHA)
                    pygame.draw.circle(trail_surf, (*NEON_ORANGE, alpha),
                                       (tr, tr), tr)
                    surface.blit(trail_surf, (tsx - tr, tsy - tr))

            # SlimeBoss toxic pools (green)
            for tx, ty, tlife, tdmg, tradius in self.toxic_pools:
                tsx, tsy = self.camera.apply(tx, ty)
                tr = self.camera.s(tradius)
                alpha = min(120, int(120 * (tlife / 3.0)))
                if tr > 0 and alpha > 0:
                    pool_surf = pygame.Surface((tr * 2, tr * 2), pygame.SRCALPHA)
                    pygame.draw.circle(pool_surf, (*NEON_GREEN, alpha),
                                       (tr, tr), tr)
                    surface.blit(pool_surf, (tsx - tr, tsy - tr))

            for enemy in self.enemies:
                enemy.draw(surface, self.camera)

            for bullet in self.enemy_bullets:
                bullet.draw(surface, self.camera)

            for bullet in self.player_bullets:
                bullet.draw(surface, self.camera)

            if self.player:
                self.player.draw(surface, self.camera)

            # Power-ups
            if self.powerup_manager:
                self.powerup_manager.draw(surface, self.camera)

            self.particles.draw(surface, self.camera)

            wave_info = self.enemy_manager.wave_info
            self.ui.draw_hud(surface, self.player, wave_info, self.fps)

            # Mini-map
            powerup_list = self.powerup_manager.powerups if self.powerup_manager else []
            self.ui.draw_minimap(
                surface, self.player, self.obstacles,
                powerup_list, self.enemies,
                boss=self.enemy_manager.active_boss)

            # Boss HP bar
            self.ui.draw_boss_hp_bar(surface, wave_info)

            if wave_info["announcing"]:
                self.ui.draw_wave_announcement(
                    surface,
                    wave_info["wave"],
                    self.enemy_manager.wave_announcement_timer,
                    is_boss=wave_info.get("boss_wave", False),
                )

            if self.state == GameState.PAUSED:
                self.ui.draw_pause_menu(surface)
            elif self.state == GameState.UPGRADE:
                self.ui.draw_upgrade_screen(surface, self.upgrade_options, self.player)
            elif self.state == GameState.GAME_OVER:
                self.ui.draw_game_over(surface, self.player, wave_info)
