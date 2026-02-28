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
    COMBO_WINDOW, SCORE_MULTIPLIER,
    COMBO_TIER1_THRESHOLD, COMBO_TIER2_THRESHOLD,
    BOMBER_EXPLOSION_RADIUS, BOMBER_DAMAGE,
    ULT_PULSE_RADIUS, ULT_PULSE_DAMAGE, ULT_PUSHBACK_FORCE,
    ULT_SLOW_DURATION, ULT_SLOW_FACTOR,
    ULT_LASER_COUNT, ULT_LASER_DAMAGE, ULT_LASER_SPEED,
    ULT_TOXIC_POOL_COUNT, ULT_TOXIC_POOL_DAMAGE,
    ULT_TOXIC_POOL_LIFETIME, ULT_TOXIC_POOL_RADIUS,
    ULT_TANK_PUSHBACK_MULT,
    TRIAL_KILL_TARGET,
)
from .obstacles import generate_obstacles, PowerUpManager
from .config import Config, resource_path, assets
from .player import Player
from .projectiles import RailgunBullet, LaserBullet
from .enemies import ShieldGuard, SuicideBomber, Boss, SniperBoss, SlimeBoss
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

        # Hover-sound tracking — fire hover.wav once when cursor enters a
        # new interactive element (menu button or upgrade card).
        self._last_hovered_id: str | None = None   # last element that triggered hover sound
        self._prev_draw_state: str | None = None   # detect state transitions

        # ── Trial Mode (Ultimate Skill Challenges) ───────
        self.trial_active = False
        self.trial_type = None         # 'sniper', 'slime', or 'tank'
        self.trial_kills = 0           # kills without taking damage
        self.trial_target = TRIAL_KILL_TARGET
        self.trial_failed = False
        self.trial_notification_timer = 0.0  # shows "Trial Started/Failed/Complete" text
        self.trial_notification_text = ""

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
        """Load SFX from asset files when available; fall back to procedurally
        generated tones so the game always has audio, even without .wav files."""
        self.sounds = {}
        # Reference volumes (0–1) before sfx_volume multiplier is applied.
        # Tune these to balance individual effects against each other.
        self._sfx_base_volumes = {
            "shoot":   0.30,
            "explode": 0.40,
            "levelup": 0.45,
            "hover":   0.25,
        }
        # Map: sound name → filename inside assets/sounds/sfx/
        _sfx_files = {
            "shoot":   "shoot.wav",
            "explode": "explode.wav",
            "levelup": "levelup.wav",
            "hover":   "hover.wav",
        }
        for name, filename in _sfx_files.items():
            loaded = False
            try:
                path = assets.sfx(filename)
                if os.path.exists(path):
                    self.sounds[name] = pygame.mixer.Sound(path)
                    loaded = True
            except Exception:
                pass
            if not loaded:
                self._load_generated_sfx(name)
        self._apply_sfx_volumes()
        self._start_bgm()

    def _load_generated_sfx(self, name):
        """Generate a synthetic fallback sound when no .wav file is available."""
        try:
            arr = None
            if name == "shoot":
                arr = self._generate_beep(440, 0.05)
            elif name == "explode":
                arr = self._generate_noise(0.1)
            elif name == "levelup":
                arr = self._generate_beep(880, 0.15)
            if arr is not None:
                self.sounds[name] = pygame.sndarray.make_sound(arr)
        except Exception:
            pass

    def _start_bgm(self):
        """Load and loop the background music track."""
        # _BGM_MASTER_SCALE caps the maximum mixer volume so the track never
        # overpowers SFX even at the 100% slider position.  Raise/lower this
        # single constant to re-tune the overall BGM loudness.
        self._BGM_MASTER_SCALE = 0.4
        try:
            bgm_path = assets.music("Sketchbook 2025-12-11_VERSE.ogg")
            if os.path.exists(bgm_path):
                pygame.mixer.music.load(bgm_path)
                pygame.mixer.music.set_volume(self.config.music_volume * self._BGM_MASTER_SCALE)
                pygame.mixer.music.play(-1)   # -1 = loop forever
        except Exception:
            pass

    def _apply_sfx_volumes(self):
        """Scale every loaded SFX Sound by config.sfx_volume."""
        for name, base in self._sfx_base_volumes.items():
            if name in self.sounds:
                try:
                    self.sounds[name].set_volume(
                        max(0.0, min(1.0, base * self.config.sfx_volume))
                    )
                except Exception:
                    pass

    def _apply_volumes(self):
        """Re-apply all audio volumes from config (call after settings change)."""
        try:
            scale = getattr(self, '_BGM_MASTER_SCALE', 0.4)
            pygame.mixer.music.set_volume(self.config.music_volume * scale)
        except Exception:
            pass
        self._apply_sfx_volumes()

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

    def _check_hover_sound(self):
        """Fire hover.wav exactly once when the mouse enters a new interactive
        element.  Compare UI's freshly-computed hovered_id against the last
        frame's value; play only on a change *to* a non-None id.
        Re-entry into a previously-hovered element after a state change also
        triggers the sound because _prev_draw_state resets _last_hovered_id."""
        current = self.ui.hovered_id
        if current is not None and current != self._last_hovered_id:
            self._play_sound("hover")
        self._last_hovered_id = current

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

        # Score / Combo
        self.score = 0
        self.combo_counter = 0
        self.combo_timer = 0.0
        self.combo_display_timer = 0.0   # cosmetic pulse timer

        # Trial state reset
        self.trial_active = False
        self.trial_type = None
        self.trial_kills = 0
        self.trial_failed = False
        self.trial_notification_timer = 0.0
        self.trial_notification_text = ""

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
                self._apply_volumes()         # re-apply volumes after display change
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
                elif event.key == pygame.K_q:
                    # Activate ultimate ability
                    if self.player and self.player.try_activate_ultimate():
                        self._play_sound("explode")
            elif self.state == GameState.PAUSED:
                if event.key == pygame.K_ESCAPE:
                    self.state = GameState.PLAYING
                elif event.key == pygame.K_s:
                    self._open_settings()
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

            elif self.state == GameState.PAUSED:
                if event.button == 1:
                    if (self.ui.pause_settings_rect is not None and
                            self.ui.pause_settings_rect.collidepoint(event.pos)):
                        self._open_settings()

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

        # ── SuicideBomber explosion check ──
        for enemy in list(self.enemies):
            if isinstance(enemy, SuicideBomber) and enemy.exploded:
                ex, ey = enemy.pos_x, enemy.pos_y
                # Massive particle explosion
                self.particles.emit_explosion(ex, ey, color=NEON_YELLOW, count=35)
                self.particles.emit_explosion(ex, ey, color=NEON_ORANGE, count=20)
                self._play_sound("explode")
                # AOE damage to player
                pdx = self.player.pos_x - ex
                pdy = self.player.pos_y - ey
                pdist = math.sqrt(pdx * pdx + pdy * pdy)
                if pdist < BOMBER_EXPLOSION_RADIUS + self.player.radius:
                    if self.player.take_damage(enemy.damage):
                        self._on_trial_damage()
                # AOE damage to other enemies caught in the blast
                for other in list(self.enemies):
                    if other is enemy:
                        continue
                    odx = other.pos_x - ex
                    ody = other.pos_y - ey
                    odist = math.sqrt(odx * odx + ody * ody)
                    if odist < BOMBER_EXPLOSION_RADIUS + other.radius:
                        other.take_damage(enemy.damage // 2, self.particles)
                # Remove the bomber and credit the kill
                enemy.hp = 0
                enemy.kill()
                self.enemy_manager.on_enemy_killed()

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
                    if self.player.take_damage(tdmg):
                        self._on_trial_damage()
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

        # ── Neon Pulse Ultimate Effects ──
        if self.player.ult_fired_this_frame:
            self._process_neon_pulse()

        # ── Trial notification timer ──
        if self.trial_notification_timer > 0:
            self.trial_notification_timer -= dt

        self.particles.update(dt)
        self._check_collisions()

        # ── Combo timer decay ──
        if self.combo_timer > 0:
            self.combo_timer -= dt
            if self.combo_timer <= 0:
                self.combo_counter = 0
                self.combo_timer = 0.0
                self.player.combo_tier = 0
        if self.combo_display_timer > 0:
            self.combo_display_timer -= dt

        if not self.player.alive:
            self.state = GameState.GAME_OVER
            self.particles.emit_explosion(self.player.pos_x, self.player.pos_y, count=30)
            self._play_sound("explode")

    # ── Neon Pulse (Ultimate) ────────────────────────────

    def _process_neon_pulse(self):
        """Apply the Neon Pulse radial blast and all augmentations."""
        px, py = self.player.pos_x, self.player.pos_y
        radius = ULT_PULSE_RADIUS
        pushback = ULT_PUSHBACK_FORCE

        # Tank augment: massive knockback
        if self.player.ult_upgrades['tank']:
            pushback *= ULT_TANK_PUSHBACK_MULT

        # Base effect: damage + pushback + slow all enemies in radius
        for enemy in list(self.enemies):
            edx = enemy.pos_x - px
            edy = enemy.pos_y - py
            edist = math.sqrt(edx * edx + edy * edy)
            if edist < radius and edist > 0:
                # Pushback
                nx = edx / edist
                ny = edy / edist
                enemy.pos_x += nx * pushback * 0.15
                enemy.pos_y += ny * pushback * 0.15
                # Damage
                enemy.take_damage(ULT_PULSE_DAMAGE, self.particles)
                # 3-second slow
                enemy.apply_slow(ULT_SLOW_DURATION, ULT_SLOW_FACTOR)

        # Destroy enemy bullets in radius
        for bullet in list(self.enemy_bullets):
            bdx = bullet.pos_x - px
            bdy = bullet.pos_y - py
            if math.sqrt(bdx * bdx + bdy * bdy) < radius:
                bullet.kill()

        # Sniper augment: fire auto-aiming lasers at nearest enemies
        if self.player.ult_upgrades['sniper']:
            targets = []
            for enemy in self.enemies:
                edx = enemy.pos_x - px
                edy = enemy.pos_y - py
                edist = math.sqrt(edx * edx + edy * edy)
                targets.append((edist, enemy))
            targets.sort(key=lambda t: t[0])
            for i in range(min(ULT_LASER_COUNT, len(targets))):
                _, target = targets[i]
                angle = math.atan2(target.pos_y - py, target.pos_x - px)
                laser = LaserBullet(px, py, angle, ULT_LASER_SPEED, ULT_LASER_DAMAGE)
                self.player_bullets.add(laser)

        # Slime augment: leave toxic pools in a ring
        if self.player.ult_upgrades['slime']:
            for i in range(ULT_TOXIC_POOL_COUNT):
                angle = (i / ULT_TOXIC_POOL_COUNT) * math.pi * 2
                pool_dist = radius * 0.6
                pool_x = px + math.cos(angle) * pool_dist
                pool_y = py + math.sin(angle) * pool_dist
                self.toxic_pools.append((
                    pool_x, pool_y,
                    ULT_TOXIC_POOL_LIFETIME,
                    ULT_TOXIC_POOL_DAMAGE,
                    ULT_TOXIC_POOL_RADIUS,
                ))
                self.particles.emit(pool_x, pool_y, NEON_GREEN, count=6,
                                    speed_range=(20, 60),
                                    lifetime_range=(0.3, 0.6),
                                    size_range=(3, 6))

    # ── Trial Mode (Challenge System) ────────────────────

    def _start_trial(self, trial_type):
        """Begin a trial challenge for unlocking an ultimate augmentation."""
        self.trial_active = True
        self.trial_type = trial_type
        self.trial_kills = 0
        self.trial_failed = False
        self.trial_notification_timer = 3.0
        self.trial_notification_text = f"TRIAL: {trial_type.upper()} — Kill {self.trial_target} without taking damage!"

    def _on_trial_kill(self):
        """Called when an enemy is killed during an active trial."""
        if not self.trial_active or self.trial_failed:
            return
        self.trial_kills += 1
        if self.trial_kills >= self.trial_target:
            # Trial complete — unlock augmentation
            self.player.ult_upgrades[self.trial_type] = True
            self.trial_active = False
            self.trial_notification_timer = 4.0
            self.trial_notification_text = f"TRIAL COMPLETE! {self.trial_type.upper()} AUGMENT UNLOCKED!"
            self._play_sound("levelup")
            # Celebration particles
            self.particles.emit_neon_pulse(
                self.player.pos_x, self.player.pos_y,
                200, augmented=True)

    def _on_trial_damage(self):
        """Called when the player takes damage during an active trial."""
        if not self.trial_active or self.trial_failed:
            return
        self.trial_failed = True
        self.trial_active = False
        self.trial_kills = 0
        self.trial_notification_timer = 3.0
        self.trial_notification_text = "TRIAL FAILED! Defeat another boss for a new artifact."

    def _award_boss_artifact(self, boss):
        """Award a boss artifact based on the boss type, then start the trial."""
        # Determine which artifact to grant based on boss class
        if isinstance(boss, SniperBoss):
            artifact_type = 'sniper'
        elif isinstance(boss, SlimeBoss):
            artifact_type = 'slime'
        else:  # Boss (tank-type)
            artifact_type = 'tank'

        # Only award if the augment isn't already unlocked
        if self.player.ult_upgrades[artifact_type]:
            return  # already unlocked

        if not self.player.boss_artifacts[artifact_type]:
            self.player.boss_artifacts[artifact_type] = True
            self.trial_notification_timer = 4.0
            self.trial_notification_text = (
                f"BOSS ARTIFACT: {artifact_type.upper()} — "
                f"Press [Q] near enemies, then complete the trial!"
            )
            # Start the trial immediately
            self._start_trial(artifact_type)

    # ── Collisions ───────────────────────────────────────

    def _check_collisions(self):
        for bullet in list(self.player_bullets):
            is_railgun = isinstance(bullet, RailgunBullet)
            for enemy in list(self.enemies):
                dx = bullet.pos_x - enemy.pos_x
                dy = bullet.pos_y - enemy.pos_y
                dist = math.sqrt(dx * dx + dy * dy)
                if dist < bullet.radius + enemy.radius:
                    # Railgun: skip enemies already pierced
                    if is_railgun and bullet.has_hit(id(enemy)):
                        continue

                    # ShieldGuard: directional front-shield immunity
                    if isinstance(enemy, ShieldGuard):
                        hit_angle = math.atan2(
                            bullet.pos_y - enemy.pos_y,
                            bullet.pos_x - enemy.pos_x)
                        killed = enemy.take_damage(
                            bullet.damage, self.particles, from_angle=hit_angle)
                        # If shielded, take_damage returns False and bullet just bounces
                        if not killed and enemy.hp > 0:
                            # Bullet was blocked — consume it (unless railgun)
                            if enemy.is_bullet_shielded(hit_angle):
                                if not is_railgun:
                                    bullet.kill()
                                else:
                                    bullet.register_hit(id(enemy))
                                if not is_railgun:
                                    break
                                continue
                    else:
                        killed = enemy.take_damage(bullet.damage, self.particles)

                    # Apply knockback if the bullet carries it
                    if hasattr(bullet, 'knockback_vx') and not killed:
                        enemy.pos_x += bullet.knockback_vx * 0.1
                        enemy.pos_y += bullet.knockback_vy * 0.1

                    if is_railgun:
                        # Railgun penetrates — record hit but do NOT kill bullet
                        bullet.register_hit(id(enemy))
                    else:
                        bullet.kill()

                    if killed:
                        # ── Combo & Score ──
                        self.combo_counter += 1
                        self.combo_timer = COMBO_WINDOW
                        combo_mult = 1 + (self.combo_counter - 1) * 0.25
                        points = int(enemy.xp_value * combo_mult * SCORE_MULTIPLIER)
                        self.score += points
                        self.combo_display_timer = 0.6  # pulse duration

                        # Milestone effects
                        if self.combo_counter == COMBO_TIER1_THRESHOLD:
                            self.particles.emit_combo_tier1(
                                self.player.pos_x, self.player.pos_y)
                            self.player.combo_tier = 1
                        elif self.combo_counter == COMBO_TIER2_THRESHOLD:
                            self.particles.emit_combo_tier2(
                                self.player.pos_x, self.player.pos_y)
                            self.player.combo_tier = 2
                        elif self.combo_counter < COMBO_TIER1_THRESHOLD:
                            self.player.combo_tier = 0

                        self._play_sound("explode")
                        self.enemy_manager.on_enemy_killed()

                        # Ultimate charge on kill
                        self.player.gain_ult_charge()
                        # Trial progress
                        self._on_trial_kill()
                        # Boss artifact drop
                        if hasattr(enemy, 'is_boss') and enemy.is_boss:
                            self._award_boss_artifact(enemy)

                        leveled = self.player.gain_xp(enemy.xp_value)
                        if leveled:
                            self.pending_levelups += 1
                            self._generate_upgrade_options()
                            self.state = GameState.UPGRADE
                            # Scale difficulty with player level
                            self.enemy_manager.set_difficulty(self.player.level)

                    if not is_railgun:
                        break

        if not self.player.is_dashing:
            for bullet in list(self.enemy_bullets):
                dx = bullet.pos_x - self.player.pos_x
                dy = bullet.pos_y - self.player.pos_y
                dist = math.sqrt(dx * dx + dy * dy)
                if dist < bullet.radius + self.player.radius:
                    if self.player.take_damage(bullet.damage):
                        self._on_trial_damage()
                    bullet.kill()

        if not self.player.is_dashing:
            for enemy in self.enemies:
                dx = enemy.pos_x - self.player.pos_x
                dy = enemy.pos_y - self.player.pos_y
                dist = math.sqrt(dx * dx + dy * dy)
                if dist < enemy.radius + self.player.radius:
                    if self.player.take_damage(enemy.damage):
                        self._on_trial_damage()

        # Boss slam damage (works for Boss, SniperBoss, SlimeBoss)
        for enemy in self.enemies:
            if hasattr(enemy, 'is_boss') and enemy.is_boss and enemy.slam_hit_player:
                # Use SlimeBoss-specific shockwave damage if applicable
                if isinstance(enemy, SlimeBoss):
                    slam_dmg = SLIME_BOSS_SHOCKWAVE_DAMAGE
                else:
                    slam_dmg = BOSS_SLAM_DAMAGE
                self.player.take_damage(slam_dmg)
                self._on_trial_damage()
                self.particles.emit_explosion(
                    self.player.pos_x, self.player.pos_y,
                    color=NEON_YELLOW, count=20)
                self._play_sound("explode")

    # ── Drawing ──────────────────────────────────────────

    def _draw(self, surface):
        # Reset hover tracking on every state transition so re-entering a
        # menu state always fires the hover sound for the first element entered.
        if self.state != self._prev_draw_state:
            self._last_hovered_id = None
        self._prev_draw_state = self.state

        if self.state == GameState.MENU:
            self.ui.draw_main_menu(surface, self.time)
            self._check_hover_sound()
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
            self.ui.draw_hud(surface, self.player, wave_info, self.fps,
                             score=self.score,
                             combo=self.combo_counter,
                             combo_timer=self.combo_timer,
                             combo_display_timer=self.combo_display_timer)

            # Mini-map
            powerup_list = self.powerup_manager.powerups if self.powerup_manager else []
            self.ui.draw_minimap(
                surface, self.player, self.obstacles,
                powerup_list, self.enemies,
                boss=self.enemy_manager.active_boss)

            # Boss HP bar
            self.ui.draw_boss_hp_bar(surface, wave_info)

            # Ultimate charge bar
            self.ui.draw_ult_bar(surface, self.player)

            # Trial progress notification
            if self.trial_active or self.trial_notification_timer > 0:
                trial_info = {
                    "active": self.trial_active,
                    "type": self.trial_type,
                    "kills": self.trial_kills,
                    "target": self.trial_target,
                    "notification_timer": self.trial_notification_timer,
                    "notification_text": self.trial_notification_text,
                    "failed": self.trial_failed,
                }
                self.ui.draw_trial_progress(surface, trial_info)

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
                self._check_hover_sound()
            elif self.state == GameState.GAME_OVER:
                self.ui.draw_game_over(surface, self.player, wave_info,
                                       score=self.score)
