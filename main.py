"""
NEON ARENA // Cyberpunk Shooter
Entry point — DPI awareness MUST be set before any other imports.
"""

# ── DPI Awareness (MUST be first, before pygame) ─────────
# Without this, Windows scales the window at >100% DPI,
# causing blurriness and incorrect resolution reporting.
import ctypes
try:
    # Per-monitor DPI awareness (best quality)
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        # Fallback: system DPI aware
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

import os
# Tell SDL to not use its own DPI scaling
os.environ['SDL_VIDEO_ALLOW_SCREENSAVER'] = '1'
os.environ.setdefault('SDL_HINT_VIDEO_HIGHDPI_DISABLED', '0')

from arena_shooter.game import Game


def main():
    game = Game()
    game.run()


if __name__ == "__main__":
    main()
