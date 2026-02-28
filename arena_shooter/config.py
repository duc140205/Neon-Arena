"""
config.py - Persistent configuration manager
Handles loading/saving settings.json and provides a Config class
for dynamic resolution, screen mode, FPS, and VSync settings.
"""

import json
import os
import sys


def _get_base_dir():
    """
    Return the directory where the .exe (or main.py) lives.

    When running from source:
        <project_root>/arena_shooter/config.py  →  base = <project_root>

    When frozen with PyInstaller --onefile:
        sys.executable = C:/.../NeonArena.exe   →  base = C:/...
        sys._MEIPASS   = %TEMP%/_MEIxxxxxx      (temp extraction, NOT writable)

    We use the *executable* directory for settings.json so user
    preferences persist across runs (the temp dir is deleted on exit).
    """
    if getattr(sys, "frozen", False):
        # Running as a PyInstaller bundle
        return os.path.dirname(sys.executable)
    else:
        # Running from source — go up one level from arena_shooter/
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def resource_path(relative_path):
    """
    Resolve path to a *bundled read-only* data file.

    In --onefile mode PyInstaller extracts data files into a temp
    folder referenced by sys._MEIPASS. Use this for assets that are
    packed into the exe and should NOT be written to.
    """
    if getattr(sys, "frozen", False):
        base = sys._MEIPASS
    else:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, relative_path)


# Path to settings file (next to the .exe or project root)
_CONFIG_DIR = _get_base_dir()
CONFIG_PATH = os.path.join(_CONFIG_DIR, "settings.json")

# ── Available options ────────────────────────────────────
RESOLUTION_OPTIONS = [
    (1280, 720),
    (1366, 768),
    (1600, 900),
    (1920, 1080),
    (2560, 1440),
]

SCREEN_MODE_OPTIONS = ["windowed", "fullscreen"]

FPS_OPTIONS = [30, 60, 120, 144, 240]
# Volume slider steps: 0 % → 100 % in 10 % increments.
VOLUME_OPTIONS = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]

# ── Defaults ─────────────────────────────────────────────
DEFAULTS = {
    "display": {
        "resolution": [1280, 720],
        "screen_mode": "windowed",
    },
    "performance": {
        "fps": 60,
        "vsync": False,
    },
    "audio": {
        "music_volume": 0.7,
        "sfx_volume": 0.7,
    },
}


class Config:
    """
    Manages game configuration with persistence to settings.json.

    The game always renders internally at a fixed LOGICAL resolution (1280x720)
    and scales up to the chosen display resolution. This ensures consistent
    gameplay regardless of the output resolution.
    """

    LOGICAL_WIDTH = 1280
    LOGICAL_HEIGHT = 720

    def __init__(self):
        # Display
        self.resolution = list(DEFAULTS["display"]["resolution"])
        self.screen_mode = DEFAULTS["display"]["screen_mode"]

        # Performance
        self.fps = DEFAULTS["performance"]["fps"]
        self.vsync = DEFAULTS["performance"]["vsync"]

        # Audio
        self.music_volume: float = DEFAULTS["audio"]["music_volume"]
        self.sfx_volume: float   = DEFAULTS["audio"]["sfx_volume"]

        # Load saved settings (if any)
        self.load()

    # ── Persistence ──────────────────────────────────────

    def load(self):
        """Load settings from settings.json. Uses defaults for missing keys."""
        try:
            if os.path.exists(CONFIG_PATH):
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)

                # Display
                display = data.get("display", {})
                res = display.get("resolution", DEFAULTS["display"]["resolution"])
                if isinstance(res, list) and len(res) == 2:
                    # Validate against allowed resolutions
                    res_tuple = tuple(res)
                    if res_tuple in RESOLUTION_OPTIONS:
                        self.resolution = list(res_tuple)
                    else:
                        self.resolution = list(DEFAULTS["display"]["resolution"])
                self.screen_mode = display.get("screen_mode", DEFAULTS["display"]["screen_mode"])
                if self.screen_mode not in SCREEN_MODE_OPTIONS:
                    self.screen_mode = DEFAULTS["display"]["screen_mode"]

                # Performance
                perf = data.get("performance", {})
                fps = perf.get("fps", DEFAULTS["performance"]["fps"])
                if fps in FPS_OPTIONS:
                    self.fps = fps
                else:
                    self.fps = DEFAULTS["performance"]["fps"]
                self.vsync = bool(perf.get("vsync", DEFAULTS["performance"]["vsync"]))

                # Audio
                audio = data.get("audio", {})
                mv = float(audio.get("music_volume", DEFAULTS["audio"]["music_volume"]))
                sv = float(audio.get("sfx_volume",   DEFAULTS["audio"]["sfx_volume"]))
                self.music_volume = max(0.0, min(1.0, mv))
                self.sfx_volume   = max(0.0, min(1.0, sv))

        except (json.JSONDecodeError, IOError, KeyError):
            # If anything goes wrong, stick with defaults
            pass

    def save(self):
        """Save current settings to settings.json."""
        data = {
            "display": {
                "resolution": self.resolution,
                "screen_mode": self.screen_mode,
            },
            "performance": {
                "fps": self.fps,
                "vsync": self.vsync,
            },
            "audio": {
                "music_volume": self.music_volume,
                "sfx_volume":   self.sfx_volume,
            },
        }
        try:
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
        except IOError:
            pass

    # ── Helpers ───────────────────────────────────────────

    @property
    def display_width(self):
        return self.resolution[0]

    @property
    def display_height(self):
        return self.resolution[1]

    @property
    def resolution_tuple(self):
        return tuple(self.resolution)

    @property
    def scale_x(self):
        """Horizontal scale factor from logical to display."""
        return self.display_width / self.LOGICAL_WIDTH

    @property
    def scale_y(self):
        """Vertical scale factor from logical to display."""
        return self.display_height / self.LOGICAL_HEIGHT

    def screen_to_logical(self, screen_x, screen_y):
        """Convert actual screen/mouse coordinates to logical coordinates."""
        lx = screen_x / self.scale_x
        ly = screen_y / self.scale_y
        return lx, ly

    @property
    def resolution_index(self):
        """Get the index of current resolution in RESOLUTION_OPTIONS."""
        t = self.resolution_tuple
        if t in RESOLUTION_OPTIONS:
            return RESOLUTION_OPTIONS.index(t)
        return 0

    @property
    def screen_mode_index(self):
        """Get the index of current screen mode in SCREEN_MODE_OPTIONS."""
        if self.screen_mode in SCREEN_MODE_OPTIONS:
            return SCREEN_MODE_OPTIONS.index(self.screen_mode)
        return 0

    @property
    def fps_index(self):
        """Get the index of current FPS in FPS_OPTIONS."""
        if self.fps in FPS_OPTIONS:
            return FPS_OPTIONS.index(self.fps)
        return 1  # default to 60

    @property
    def music_volume_index(self) -> int:
        """Closest index into VOLUME_OPTIONS for the current music_volume."""
        return min(range(len(VOLUME_OPTIONS)),
                   key=lambda i: abs(VOLUME_OPTIONS[i] - self.music_volume))

    @property
    def sfx_volume_index(self) -> int:
        """Closest index into VOLUME_OPTIONS for the current sfx_volume."""
        return min(range(len(VOLUME_OPTIONS)),
                   key=lambda i: abs(VOLUME_OPTIONS[i] - self.sfx_volume))

    def resolution_label(self):
        return f"{self.resolution[0]}x{self.resolution[1]}"

    def __repr__(self):
        return (
            f"Config(res={self.resolution_label()}, "
            f"mode={self.screen_mode}, "
            f"fps={self.fps}, vsync={self.vsync})"
        )


# ── Asset path helpers ────────────────────────────────────────────────────────

class AssetManager:
    """
    Central registry for asset paths.

    All returned paths go through ``resource_path()`` so they work both when
    running from source and when frozen into a PyInstaller .exe.

    Directory layout expected under the project / bundle root:
        assets/
          icons/   – .ico files
          images/  – .png / .jpg screenshots and textures
          sounds/
            sfx/   – short sound effects (.wav / .ogg)
            music/ – background music tracks (.ogg / .mp3)

    Usage::

        from arena_shooter.config import assets

        icon   = assets.icon("neonarena.ico")
        image  = assets.image("mainmenu.png")
        sound  = assets.sfx("shoot.wav")
        track  = assets.music("theme.ogg")
    """

    _ICONS  = os.path.join("assets", "icons")
    _IMAGES = os.path.join("assets", "images")
    _SFX    = os.path.join("assets", "sounds", "sfx")
    _MUSIC  = os.path.join("assets", "sounds", "music")

    def icon(self, name: str) -> str:
        """Return the absolute path for an icon file (assets/icons/<name>)."""
        return resource_path(os.path.join(self._ICONS, name))

    def image(self, name: str) -> str:
        """Return the absolute path for an image file (assets/images/<name>)."""
        return resource_path(os.path.join(self._IMAGES, name))

    def sfx(self, name: str) -> str:
        """Return the absolute path for a sound-effect file (assets/sounds/sfx/<name>)."""
        return resource_path(os.path.join(self._SFX, name))

    def music(self, name: str) -> str:
        """Return the absolute path for a music file (assets/sounds/music/<name>)."""
        return resource_path(os.path.join(self._MUSIC, name))


# Module-level singleton — import and use directly:
#   from arena_shooter.config import assets
#   pygame.mixer.music.load(assets.music("theme.ogg"))
assets = AssetManager()
