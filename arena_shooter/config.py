"""
config.py - Persistent configuration manager
Handles loading/saving settings.json and provides a Config class
for dynamic resolution, screen mode, FPS, and VSync settings.
"""

import json
import os

# Path to settings file (next to the running script)
_CONFIG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(_CONFIG_DIR, "settings.json")

# ── Available options ────────────────────────────────────
RESOLUTION_OPTIONS = [
    (1280, 720),
    (1366, 768),
    (1600, 900),
    (1920, 1080),
    (2560, 1440),
]

SCREEN_MODE_OPTIONS = ["windowed", "fullscreen", "borderless"]

FPS_OPTIONS = [30, 60, 120, 144, 240]

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

    def resolution_label(self):
        return f"{self.resolution[0]}x{self.resolution[1]}"

    def __repr__(self):
        return (
            f"Config(res={self.resolution_label()}, "
            f"mode={self.screen_mode}, "
            f"fps={self.fps}, vsync={self.vsync})"
        )
