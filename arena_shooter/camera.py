"""
camera.py - Scale-aware smooth-follow camera system
Renders at native resolution while maintaining a consistent field of view.

The camera always shows a BASE_WIDTH x BASE_HEIGHT (1280x720) area of the
game world, regardless of actual screen resolution. The `scale` factor
converts world units to screen pixels.
"""

import pygame
from .settings import ARENA_WIDTH, ARENA_HEIGHT

# Base viewport in world units (consistent FOV at any resolution)
BASE_WIDTH = 1280
BASE_HEIGHT = 720


class Camera:
    """Scale-aware camera: consistent FOV, native resolution rendering."""

    def __init__(self, view_width=1280, view_height=720):
        self.x = 0.0
        self.y = 0.0
        self.lerp_speed = 5.0

        # Actual screen pixel dimensions
        self.view_width = view_width
        self.view_height = view_height

        # Scale: screen pixels per world unit
        self.scale = view_width / BASE_WIDTH

    def resize(self, view_width, view_height):
        """Update for a new screen resolution."""
        self.view_width = view_width
        self.view_height = view_height
        self.scale = view_width / BASE_WIDTH

    def update(self, target_x, target_y, dt):
        """Smoothly follow the target. Viewport is always BASE_WxBASE_H in world space."""
        target_cam_x = target_x - BASE_WIDTH / 2
        target_cam_y = target_y - BASE_HEIGHT / 2

        self.x += (target_cam_x - self.x) * self.lerp_speed * dt
        self.y += (target_cam_y - self.y) * self.lerp_speed * dt

        # Clamp to arena bounds (in world units)
        self.x = max(0, min(self.x, ARENA_WIDTH - BASE_WIDTH))
        self.y = max(0, min(self.y, ARENA_HEIGHT - BASE_HEIGHT))

    def apply(self, world_x, world_y):
        """Convert world coordinates to screen pixels (with scaling)."""
        sx = (world_x - self.x) * self.scale
        sy = (world_y - self.y) * self.scale
        return int(sx), int(sy)

    def s(self, pixels):
        """Scale a base-resolution pixel value to current resolution. Returns int >= 1."""
        return max(1, int(pixels * self.scale))

    def sf(self, pixels):
        """Scale a pixel value, returning float."""
        return max(1.0, pixels * self.scale)

    def apply_rect(self, rect):
        """Apply camera offset + scaling to a world-space rect."""
        return pygame.Rect(
            int((rect.x - self.x) * self.scale),
            int((rect.y - self.y) * self.scale),
            int(rect.width * self.scale),
            int(rect.height * self.scale),
        )

    def world_pos(self, screen_x, screen_y):
        """Convert screen pixel coordinates back to world coordinates."""
        wx = screen_x / self.scale + self.x
        wy = screen_y / self.scale + self.y
        return wx, wy

    @property
    def rect(self):
        """Visible area in world coordinates (always BASE_WIDTH x BASE_HEIGHT)."""
        return pygame.Rect(int(self.x), int(self.y), BASE_WIDTH, BASE_HEIGHT)
