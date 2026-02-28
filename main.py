"""
NEON ARENA // Cyberpunk Shooter
Entry point — DPI awareness MUST be set before any other imports.
"""

# ── DPI Awareness (MUST be first, before pygame) ─────────
# Level 1 (System_DPI_Aware): Windows DPI-scales the app uniformly, so
# pygame receives logical pixels and set_mode((1280,720)) produces a
# genuine 1280×720 window on any DPI setting.
# Level 2 (Per_Monitor) makes SDL work in physical pixels, which causes
# a 1280×720 request to be rendered at 2560×1440 on a 200% DPI screen.
import ctypes
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)  # System_DPI_Aware
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

import os
# Disable SDL2's built-in HiDPI surface scaling.
# Without this, SDL may silently double the surface dimensions on HiDPI
# displays even when DPI awareness is already handled by Windows.
os.environ['SDL_VIDEO_HIGHDPI_DISABLED'] = '1'
os.environ['SDL_VIDEO_ALLOW_SCREENSAVER'] = '1'

from arena_shooter.game import Game


def main():
    game = Game()
    game.run()


if __name__ == "__main__":
    main()
