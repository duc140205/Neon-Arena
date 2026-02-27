"""
enemies.py - Enemy types: Chaser, Shooter, Tank
All drawing uses camera.s() for native-resolution rendering.
"""

import pygame
import math
import random
from .settings import (
    CHASER_SPEED, CHASER_HP, CHASER_SIZE, CHASER_DAMAGE, CHASER_XP, CHASER_COLOR,
    SHOOTER_SPEED, SHOOTER_HP, SHOOTER_SIZE, SHOOTER_DAMAGE, SHOOTER_XP, SHOOTER_COLOR,
    SHOOTER_FIRE_RATE, SHOOTER_BULLET_SPEED, SHOOTER_PREFERRED_DIST,
    TANK_SPEED, TANK_HP, TANK_SIZE, TANK_DAMAGE, TANK_XP, TANK_COLOR,
    NEON_RED, NEON_ORANGE, NEON_PURPLE, WHITE,
    ARENA_WIDTH, ARENA_HEIGHT,
)
from .projectiles import EnemyBullet


class Enemy(pygame.sprite.Sprite):
    """Base enemy class."""

    def __init__(self, x, y, speed, hp, size, damage, xp, color):
        super().__init__()
        self.pos_x = float(x)
        self.pos_y = float(y)
        self.speed = speed
        self.hp = hp
        self.max_hp = hp
        self.radius = size
        self.damage = damage
        self.xp_value = xp
        self.color = color
        self.flash_timer = 0.0

        self.image = pygame.Surface((size * 2 + 4, size * 2 + 4), pygame.SRCALPHA)
        self.rect = self.image.get_rect(center=(int(x), int(y)))

        self.wobble_offset = random.uniform(0, math.pi * 2)
        self.wobble_speed = random.uniform(2, 4)

    def take_damage(self, amount, particle_system):
        self.hp -= amount
        self.flash_timer = 0.1
        if self.hp <= 0:
            self.hp = 0
            particle_system.emit_explosion(self.pos_x, self.pos_y, self.color, count=15)
            self.kill()
            return True
        else:
            particle_system.emit(self.pos_x, self.pos_y, self.color, count=5,
                                 speed_range=(40, 120), lifetime_range=(0.1, 0.3))
        return False

    def update(self, dt, player_x, player_y, enemy_bullets=None):
        self.flash_timer = max(0, self.flash_timer - dt)
        self.pos_x = max(self.radius, min(ARENA_WIDTH - self.radius, self.pos_x))
        self.pos_y = max(self.radius, min(ARENA_HEIGHT - self.radius, self.pos_y))
        self.rect.centerx = int(self.pos_x)
        self.rect.centery = int(self.pos_y)

    def draw(self, surface, camera):
        """Draw with neon glow effect, using camera.s() for scaling."""
        sx, sy = camera.apply(self.pos_x, self.pos_y)
        sc = camera.s

        # Off-screen check (with scaled margin)
        margin = sc(self.radius + 20)
        sw, sh = surface.get_size()
        if sx < -margin or sx > sw + margin:
            return
        if sy < -margin or sy > sh + margin:
            return

        color = WHITE if self.flash_timer > 0 else self.color

        # Glow
        glow_r = sc(self.radius + 8)
        glow_surf = pygame.Surface((glow_r * 2, glow_r * 2), pygame.SRCALPHA)
        pygame.draw.circle(glow_surf, (*self.color, 40), (glow_r, glow_r), glow_r)
        surface.blit(glow_surf, (sx - glow_r, sy - glow_r))

        # Shape (subclass override)
        self._draw_shape(surface, sx, sy, color, camera)

        # HP bar (only if damaged)
        if self.hp < self.max_hp:
            bar_w = sc(self.radius * 2)
            bar_h = max(2, sc(4))
            bar_x = sx - bar_w // 2
            bar_y = sy - sc(self.radius) - sc(10)
            pygame.draw.rect(surface, (40, 40, 60), (bar_x, bar_y, bar_w, bar_h))
            fill_w = int(bar_w * (self.hp / self.max_hp))
            pygame.draw.rect(surface, NEON_RED, (bar_x, bar_y, fill_w, bar_h))

    def _draw_shape(self, surface, sx, sy, color, camera):
        """Default: circle."""
        r = camera.s(self.radius)
        pygame.draw.circle(surface, color, (sx, sy), r, max(1, camera.s(2)))
        inner_r = r - camera.s(2)
        if inner_r > 1:
            inner_surf = pygame.Surface((inner_r * 2, inner_r * 2), pygame.SRCALPHA)
            pygame.draw.circle(inner_surf, (*color, 60), (inner_r, inner_r), inner_r)
            surface.blit(inner_surf, (sx - inner_r, sy - inner_r))


class Chaser(Enemy):
    """Rushes directly toward the player."""

    def __init__(self, x, y, hp_multiplier=1.0, speed_multiplier=1.0):
        super().__init__(
            x, y,
            speed=CHASER_SPEED * speed_multiplier,
            hp=int(CHASER_HP * hp_multiplier),
            size=CHASER_SIZE,
            damage=CHASER_DAMAGE,
            xp=CHASER_XP,
            color=CHASER_COLOR,
        )

    def update(self, dt, player_x, player_y, enemy_bullets=None):
        dx = player_x - self.pos_x
        dy = player_y - self.pos_y
        dist = math.sqrt(dx * dx + dy * dy)
        if dist > 0:
            dx /= dist
            dy /= dist
        wobble = math.sin(pygame.time.get_ticks() * 0.005 + self.wobble_offset) * 0.3
        perp_x = -dy * wobble
        perp_y = dx * wobble
        self.pos_x += (dx + perp_x) * self.speed * dt
        self.pos_y += (dy + perp_y) * self.speed * dt
        super().update(dt, player_x, player_y)

    def _draw_shape(self, surface, sx, sy, color, camera):
        """Draw as a triangle pointing toward last movement direction."""
        r = camera.s(self.radius)
        points = [
            (sx, sy - r),
            (sx + r, sy + r),
            (sx - r, sy + r),
        ]
        pygame.draw.polygon(surface, color, points, max(1, camera.s(2)))

        # Inner fill
        inset = camera.s(3)
        inner_points = [
            (sx, sy - r + inset),
            (sx + r - inset, sy + r - camera.s(2)),
            (sx - r + inset, sy + r - camera.s(2)),
        ]
        pad = r + camera.s(2)
        inner_surf = pygame.Surface((pad * 2, pad * 2), pygame.SRCALPHA)
        shifted = [(p[0] - sx + pad, p[1] - sy + pad) for p in inner_points]
        pygame.draw.polygon(inner_surf, (*color, 60), shifted)
        surface.blit(inner_surf, (sx - pad, sy - pad))


class Shooter(Enemy):
    """Keeps distance from the player and fires projectiles."""

    def __init__(self, x, y, hp_multiplier=1.0, speed_multiplier=1.0):
        super().__init__(
            x, y,
            speed=SHOOTER_SPEED * speed_multiplier,
            hp=int(SHOOTER_HP * hp_multiplier),
            size=SHOOTER_SIZE,
            damage=SHOOTER_DAMAGE,
            xp=SHOOTER_XP,
            color=SHOOTER_COLOR,
        )
        self.fire_timer = random.uniform(0, SHOOTER_FIRE_RATE)
        self.fire_rate = SHOOTER_FIRE_RATE
        self.preferred_dist = SHOOTER_PREFERRED_DIST

    def update(self, dt, player_x, player_y, enemy_bullets=None):
        dx = player_x - self.pos_x
        dy = player_y - self.pos_y
        dist = math.sqrt(dx * dx + dy * dy)
        if dist > 0:
            ndx = dx / dist
            ndy = dy / dist
        else:
            ndx, ndy = 0, 0

        if dist > self.preferred_dist + 30:
            self.pos_x += ndx * self.speed * dt
            self.pos_y += ndy * self.speed * dt
        elif dist < self.preferred_dist - 30:
            self.pos_x -= ndx * self.speed * dt
            self.pos_y -= ndy * self.speed * dt
        else:
            strafe = math.sin(pygame.time.get_ticks() * 0.002 + self.wobble_offset)
            self.pos_x += (-ndy * strafe) * self.speed * dt
            self.pos_y += (ndx * strafe) * self.speed * dt

        self.fire_timer -= dt
        if self.fire_timer <= 0 and enemy_bullets is not None:
            self.fire_timer = self.fire_rate
            angle = math.atan2(dy, dx)
            bullet = EnemyBullet(
                self.pos_x, self.pos_y, angle,
                SHOOTER_BULLET_SPEED, self.damage,
            )
            enemy_bullets.add(bullet)

        super().update(dt, player_x, player_y)

    def _draw_shape(self, surface, sx, sy, color, camera):
        """Draw as a diamond/rhombus shape."""
        r = camera.s(self.radius)
        points = [
            (sx, sy - r),
            (sx + r, sy),
            (sx, sy + r),
            (sx - r, sy),
        ]
        pygame.draw.polygon(surface, color, points, max(1, camera.s(2)))

        pad = r + camera.s(2)
        inner_surf = pygame.Surface((pad * 2, pad * 2), pygame.SRCALPHA)
        shifted = [(p[0] - sx + pad, p[1] - sy + pad) for p in points]
        pygame.draw.polygon(inner_surf, (*color, 50), shifted)
        surface.blit(inner_surf, (sx - pad, sy - pad))

        # Eye dot
        pygame.draw.circle(surface, color, (sx, sy), max(1, camera.s(3)))


class Tank(Enemy):
    """Slow, high-HP enemy that charges at the player."""

    def __init__(self, x, y, hp_multiplier=1.0, speed_multiplier=1.0):
        super().__init__(
            x, y,
            speed=TANK_SPEED * speed_multiplier,
            hp=int(TANK_HP * hp_multiplier),
            size=TANK_SIZE,
            damage=TANK_DAMAGE,
            xp=TANK_XP,
            color=TANK_COLOR,
        )
        self.charge_timer = 3.0
        self.is_charging = False
        self.charge_duration = 1.0
        self.charge_vx = 0
        self.charge_vy = 0

    def update(self, dt, player_x, player_y, enemy_bullets=None):
        dx = player_x - self.pos_x
        dy = player_y - self.pos_y
        dist = math.sqrt(dx * dx + dy * dy)

        if self.is_charging:
            self.charge_duration -= dt
            self.pos_x += self.charge_vx * dt
            self.pos_y += self.charge_vy * dt
            if self.charge_duration <= 0:
                self.is_charging = False
                self.charge_timer = 2.0 + random.uniform(0, 1.5)
        else:
            if dist > 0:
                ndx = dx / dist
                ndy = dy / dist
                self.pos_x += ndx * self.speed * dt
                self.pos_y += ndy * self.speed * dt

            self.charge_timer -= dt
            if self.charge_timer <= 0 and dist < 400:
                self.is_charging = True
                self.charge_duration = 0.6
                if dist > 0:
                    self.charge_vx = (dx / dist) * self.speed * 5
                    self.charge_vy = (dy / dist) * self.speed * 5

        super().update(dt, player_x, player_y)

    def _draw_shape(self, surface, sx, sy, color, camera):
        """Draw as a hexagon."""
        r = camera.s(self.radius)
        points = []
        for i in range(6):
            angle = math.pi / 6 + i * math.pi / 3
            px = sx + math.cos(angle) * r
            py = sy + math.sin(angle) * r
            points.append((int(px), int(py)))

        width = max(1, camera.s(3 if self.is_charging else 2))
        draw_color = WHITE if self.is_charging else color
        pygame.draw.polygon(surface, draw_color, points, width)

        # Inner fill
        pad = r + camera.s(2)
        inner_surf = pygame.Surface((pad * 2, pad * 2), pygame.SRCALPHA)
        shifted = [(p[0] - sx + pad, p[1] - sy + pad) for p in points]
        alpha = 80 if self.is_charging else 40
        pygame.draw.polygon(inner_surf, (*color, alpha), shifted)
        surface.blit(inner_surf, (sx - pad, sy - pad))

        # Inner ring
        pygame.draw.circle(surface, draw_color, (sx, sy), max(1, r // 2), max(1, camera.s(1)))
