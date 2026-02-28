"""
projectiles.py - Player and enemy bullet sprites
Drawing uses camera.s() for native-resolution rendering.
"""

import pygame
import math
from .settings import (
    NEON_CYAN, NEON_ORANGE, NEON_BLUE, NEON_MAGENTA, ARENA_WIDTH, ARENA_HEIGHT,
    PLAYER_BULLET_SIZE, BULLET_KNOCKBACK_FACTOR,
    RAILGUN_BULLET_SPEED, RAILGUN_DAMAGE_MULT, RAILGUN_SIZE,
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
        # Knockback: direction & magnitude derived from bullet velocity
        self.knockback_vx = self.vx * BULLET_KNOCKBACK_FACTOR
        self.knockback_vy = self.vy * BULLET_KNOCKBACK_FACTOR


class EnemyBullet(Bullet):
    def __init__(self, x, y, angle, speed, damage, color=NEON_ORANGE, size=None):
        super().__init__(x, y, angle, speed, damage, color, size or 4, owner="enemy")


class RailgunBullet(Bullet):
    """Piercing railgun projectile — passes through all enemies without dying."""

    def __init__(self, x, y, angle, speed, damage, color=NEON_BLUE, size=None):
        super().__init__(x, y, angle, speed, damage, color, size or RAILGUN_SIZE, owner="player")
        # Knockback (same mechanic as normal bullets)
        self.knockback_vx = self.vx * BULLET_KNOCKBACK_FACTOR
        self.knockback_vy = self.vy * BULLET_KNOCKBACK_FACTOR
        # Track which enemies were already hit so we don’t damage them every frame
        self._hit_ids: set = set()

    def has_hit(self, enemy_id: int) -> bool:
        """Return True if this enemy was already damaged by this bullet."""
        return enemy_id in self._hit_ids

    def register_hit(self, enemy_id: int):
        self._hit_ids.add(enemy_id)

    def draw(self, surface, camera):
        """Override: elongated railgun tracer with bright glow."""
        sx, sy = camera.apply(self.pos_x, self.pos_y)
        sc = camera.s
        r = sc(self.radius)

        margin = r + sc(20)
        sw, sh = surface.get_size()
        if sx < -margin or sx > sw + margin or sy < -margin or sy > sh + margin:
            return

        # Elongated glow trail
        trail_len = sc(18)
        tx = sx - math.cos(self.angle) * trail_len
        ty = sy - math.sin(self.angle) * trail_len
        pygame.draw.line(surface, (*self.color, 120), (int(tx), int(ty)),
                         (int(sx), int(sy)), max(1, r))

        # Bright core
        glow_r = r + sc(3)
        glow_surf = pygame.Surface((glow_r * 2, glow_r * 2), pygame.SRCALPHA)
        pygame.draw.circle(glow_surf, (*self.color, 80), (glow_r, glow_r), glow_r)
        surface.blit(glow_surf, (sx - glow_r, sy - glow_r))

        center_color = (
            min(255, self.color[0] + 120),
            min(255, self.color[1] + 120),
            min(255, self.color[2] + 120),
        )
        pygame.draw.circle(surface, center_color, (sx, sy), max(1, r))


class LaserBullet(Bullet):
    """Auto-aiming laser projectile spawned by the Neon Pulse sniper augment."""

    def __init__(self, x, y, angle, speed, damage, color=NEON_MAGENTA, size=None):
        super().__init__(x, y, angle, speed, damage, color, size or 6, owner="player")
        self.knockback_vx = self.vx * BULLET_KNOCKBACK_FACTOR
        self.knockback_vy = self.vy * BULLET_KNOCKBACK_FACTOR

    def draw(self, surface, camera):
        """Draw as a bright elongated laser beam."""
        sx, sy = camera.apply(self.pos_x, self.pos_y)
        sc = camera.s
        r = sc(self.radius)

        margin = r + sc(20)
        sw, sh = surface.get_size()
        if sx < -margin or sx > sw + margin or sy < -margin or sy > sh + margin:
            return

        # Elongated glow trail
        trail_len = sc(22)
        tx = sx - math.cos(self.angle) * trail_len
        ty = sy - math.sin(self.angle) * trail_len
        pygame.draw.line(surface, (*self.color, 150), (int(tx), int(ty)),
                         (int(sx), int(sy)), max(1, r))

        # Bright core
        glow_r = r + sc(4)
        glow_surf = pygame.Surface((glow_r * 2, glow_r * 2), pygame.SRCALPHA)
        pygame.draw.circle(glow_surf, (*self.color, 100), (glow_r, glow_r), glow_r)
        surface.blit(glow_surf, (sx - glow_r, sy - glow_r))

        center_color = (
            min(255, self.color[0] + 150),
            min(255, self.color[1] + 150),
            min(255, self.color[2] + 150),
        )
        pygame.draw.circle(surface, center_color, (sx, sy), max(1, r))
