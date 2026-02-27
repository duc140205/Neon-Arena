"""
projectiles.py - Player and enemy bullet sprites
Drawing uses camera.s() for native-resolution rendering.
"""

import pygame
import math
from .settings import (
    NEON_CYAN, NEON_ORANGE, ARENA_WIDTH, ARENA_HEIGHT,
    PLAYER_BULLET_SIZE
)


class Bullet(pygame.sprite.Sprite):
    """Base bullet class for both player and enemy projectiles."""

    def __init__(self, x, y, angle, speed, damage, color, size=None, owner="player"):
        super().__init__()
        self.radius = size or PLAYER_BULLET_SIZE
        self.color = color
        self.owner = owner
        self.image = pygame.Surface((4, 4), pygame.SRCALPHA)  # placeholder
        self.rect = self.image.get_rect(center=(int(x), int(y)))
        self.pos_x = float(x)
        self.pos_y = float(y)
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.speed = speed
        self.damage = damage
        self.angle = angle
        self.lifetime = 3.0

    def update(self, dt):
        self.pos_x += self.vx * dt
        self.pos_y += self.vy * dt
        self.rect.centerx = int(self.pos_x)
        self.rect.centery = int(self.pos_y)
        self.lifetime -= dt
        if (self.lifetime <= 0 or
            self.pos_x < -50 or self.pos_x > ARENA_WIDTH + 50 or
            self.pos_y < -50 or self.pos_y > ARENA_HEIGHT + 50):
            self.kill()

    def draw(self, surface, camera):
        sx, sy = camera.apply(self.pos_x, self.pos_y)
        sc = camera.s
        r = sc(self.radius)

        # Off-screen check
        margin = r + sc(10)
        sw, sh = surface.get_size()
        if sx < -margin or sx > sw + margin or sy < -margin or sy > sh + margin:
            return

        # Glow
        glow_r = r + sc(2)
        glow_surf = pygame.Surface((glow_r * 2, glow_r * 2), pygame.SRCALPHA)
        pygame.draw.circle(glow_surf, (*self.color, 60),
                           (glow_r, glow_r), glow_r)
        surface.blit(glow_surf, (sx - glow_r, sy - glow_r))

        # Core
        pygame.draw.circle(surface, self.color, (sx, sy), r)

        # Bright center
        center_color = (
            min(255, self.color[0] + 100),
            min(255, self.color[1] + 100),
            min(255, self.color[2] + 100),
        )
        cr = max(1, r // 2)
        pygame.draw.circle(surface, center_color, (sx, sy), cr)


class PlayerBullet(Bullet):
    def __init__(self, x, y, angle, speed, damage, color=NEON_CYAN, size=None):
        super().__init__(x, y, angle, speed, damage, color, size, owner="player")


class EnemyBullet(Bullet):
    def __init__(self, x, y, angle, speed, damage, color=NEON_ORANGE, size=None):
        super().__init__(x, y, angle, speed, damage, color, size or 4, owner="enemy")
