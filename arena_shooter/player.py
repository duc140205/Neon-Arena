"""
player.py - Player sprite with WASD movement, mouse aiming, shooting, and dash
All drawing uses camera.s() for native-resolution rendering.
"""

import pygame
import math
from .settings import (
    PLAYER_SPEED, PLAYER_SIZE, PLAYER_MAX_HP, PLAYER_FIRE_RATE,
    PLAYER_BULLET_SPEED, PLAYER_BULLET_DAMAGE, PLAYER_BULLET_SIZE,
    DASH_SPEED, DASH_DURATION, DASH_COOLDOWN, DASH_PARTICLES,
    NEON_CYAN, NEON_MAGENTA, NEON_PINK, WHITE,
    ARENA_WIDTH, ARENA_HEIGHT,
    BASE_XP_REQUIRED, XP_SCALE_FACTOR,
)
from .projectiles import PlayerBullet


class Player(pygame.sprite.Sprite):
    """The player character with movement, aiming, shooting, and dash."""

    def __init__(self, x, y, particle_system):
        super().__init__()
        self.radius = PLAYER_SIZE
        self.pos_x = float(x)
        self.pos_y = float(y)
        self.particles = particle_system

        self.image = pygame.Surface((self.radius * 2 + 4, self.radius * 2 + 4), pygame.SRCALPHA)
        self.rect = self.image.get_rect(center=(int(x), int(y)))

        # Stats
        self.max_hp = PLAYER_MAX_HP
        self.hp = self.max_hp
        self.speed = PLAYER_SPEED
        self.fire_rate = PLAYER_FIRE_RATE
        self.bullet_speed = PLAYER_BULLET_SPEED
        self.bullet_damage = PLAYER_BULLET_DAMAGE
        self.bullet_size = PLAYER_BULLET_SIZE

        # Dash
        self.dash_speed = DASH_SPEED
        self.dash_duration = DASH_DURATION
        self.dash_cooldown = DASH_COOLDOWN
        self.dash_timer = 0.0
        self.dash_cooldown_timer = 0.0
        self.is_dashing = False
        self.dash_vx = 0.0
        self.dash_vy = 0.0

        # Shooting
        self.fire_timer = 0.0
        self.aim_angle = 0.0

        # XP / Leveling
        self.xp = 0
        self.level = 1
        self.xp_required = BASE_XP_REQUIRED

        self.upgrade_levels = {
            "fire_rate": 0, "bullet_speed": 0, "max_hp": 0,
            "damage": 0, "move_speed": 0, "dash_cooldown": 0,
        }

        # Invincibility
        self.invincible_timer = 0.0
        self.invincible_duration = 0.5
        self.flash_timer = 0.0

    def take_damage(self, amount):
        if self.invincible_timer > 0 or self.is_dashing:
            return False
        self.hp -= amount
        self.invincible_timer = self.invincible_duration
        self.flash_timer = 0.2
        self.particles.emit(self.pos_x, self.pos_y, NEON_PINK, count=10,
                            speed_range=(60, 180), lifetime_range=(0.2, 0.5))
        if self.hp <= 0:
            self.hp = 0
        return True

    def gain_xp(self, amount):
        self.xp += amount
        self.particles.emit_xp(self.pos_x, self.pos_y)
        if self.xp >= self.xp_required:
            self.xp -= self.xp_required
            self.level += 1
            self.xp_required = int(BASE_XP_REQUIRED * (XP_SCALE_FACTOR ** (self.level - 1)))
            self.particles.emit_levelup(self.pos_x, self.pos_y)
            self.hp = min(self.max_hp, self.hp + 20)
            return True
        return False

    def apply_upgrade(self, upgrade_key):
        self.upgrade_levels[upgrade_key] += 1
        if upgrade_key == "fire_rate":
            self.fire_rate *= 0.80
        elif upgrade_key == "bullet_speed":
            self.bullet_speed *= 1.15
        elif upgrade_key == "max_hp":
            self.max_hp += 25
            self.hp = min(self.max_hp, self.hp + 25)
        elif upgrade_key == "damage":
            self.bullet_damage *= 1.20
        elif upgrade_key == "move_speed":
            self.speed *= 1.10
        elif upgrade_key == "dash_cooldown":
            self.dash_cooldown *= 0.85

    def update(self, dt, mouse_screen_pos, camera):
        self.fire_timer = max(0, self.fire_timer - dt)
        self.invincible_timer = max(0, self.invincible_timer - dt)
        self.flash_timer = max(0, self.flash_timer - dt)
        self.dash_cooldown_timer = max(0, self.dash_cooldown_timer - dt)

        keys = pygame.key.get_pressed()

        if self.is_dashing:
            self.dash_timer -= dt
            self.pos_x += self.dash_vx * dt
            self.pos_y += self.dash_vy * dt
            if int(self.dash_timer * 60) % 2 == 0:
                self.particles.emit(self.pos_x, self.pos_y, NEON_MAGENTA, count=3,
                                    speed_range=(30, 100), lifetime_range=(0.15, 0.35),
                                    size_range=(3, 6))
            if self.dash_timer <= 0:
                self.is_dashing = False
        else:
            dx, dy = 0.0, 0.0
            if keys[pygame.K_w] or keys[pygame.K_UP]:
                dy -= 1
            if keys[pygame.K_s] or keys[pygame.K_DOWN]:
                dy += 1
            if keys[pygame.K_a] or keys[pygame.K_LEFT]:
                dx -= 1
            if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
                dx += 1

            if dx != 0 and dy != 0:
                length = math.sqrt(dx * dx + dy * dy)
                dx /= length
                dy /= length

            self.pos_x += dx * self.speed * dt
            self.pos_y += dy * self.speed * dt

            if keys[pygame.K_SPACE] and self.dash_cooldown_timer <= 0 and (dx != 0 or dy != 0):
                self.is_dashing = True
                self.dash_timer = self.dash_duration
                self.dash_cooldown_timer = self.dash_cooldown
                self.dash_vx = dx * self.dash_speed
                self.dash_vy = dy * self.dash_speed
                self.particles.emit_dash(self.pos_x, self.pos_y, NEON_MAGENTA, DASH_PARTICLES)

        self.pos_x = max(self.radius, min(ARENA_WIDTH - self.radius, self.pos_x))
        self.pos_y = max(self.radius, min(ARENA_HEIGHT - self.radius, self.pos_y))
        self.rect.centerx = int(self.pos_x)
        self.rect.centery = int(self.pos_y)

        # Aim at mouse (mouse_screen_pos is already in screen pixels)
        mouse_world_x, mouse_world_y = camera.world_pos(*mouse_screen_pos)
        self.aim_angle = math.atan2(mouse_world_y - self.pos_y, mouse_world_x - self.pos_x)

    def try_shoot(self, bullet_group):
        mouse_buttons = pygame.mouse.get_pressed()
        if mouse_buttons[0] and self.fire_timer <= 0 and not self.is_dashing:
            self.fire_timer = self.fire_rate
            gun_dist = self.radius + 8
            bx = self.pos_x + math.cos(self.aim_angle) * gun_dist
            by = self.pos_y + math.sin(self.aim_angle) * gun_dist
            bullet = PlayerBullet(bx, by, self.aim_angle,
                                  self.bullet_speed, self.bullet_damage,
                                  size=self.bullet_size)
            bullet_group.add(bullet)
            self.particles.emit(bx, by, NEON_CYAN, count=4,
                                speed_range=(50, 150), lifetime_range=(0.1, 0.2),
                                size_range=(2, 4),
                                angle_range=(self.aim_angle - 0.3, self.aim_angle + 0.3))
            return True
        return False

    def draw(self, surface, camera):
        """Draw player at native resolution using camera.s() for scaling."""
        sx, sy = camera.apply(self.pos_x, self.pos_y)
        sc = camera.s  # shorthand for scaling

        # ── Glow ──
        glow_r = sc(self.radius + 12)
        glow_surf = pygame.Surface((glow_r * 2, glow_r * 2), pygame.SRCALPHA)
        glow_alpha = 30
        if self.is_dashing:
            glow_alpha = 60
        if self.invincible_timer > 0:
            glow_alpha = 15 + int(45 * abs(math.sin(self.invincible_timer * 15)))
        pygame.draw.circle(glow_surf, (*NEON_CYAN, glow_alpha),
                           (glow_r, glow_r), glow_r)
        surface.blit(glow_surf, (sx - glow_r, sy - glow_r))

        # ── Body ──
        body_color = NEON_CYAN
        if self.flash_timer > 0:
            body_color = WHITE
        elif self.is_dashing:
            body_color = NEON_MAGENTA

        r = sc(self.radius)
        pygame.draw.circle(surface, body_color, (sx, sy), r, max(1, sc(2)))
        inner_r = r - sc(4)
        if inner_r > 0:
            inner_surf = pygame.Surface((inner_r * 2, inner_r * 2), pygame.SRCALPHA)
            pygame.draw.circle(inner_surf, (*body_color, 80),
                               (inner_r, inner_r), inner_r)
            surface.blit(inner_surf, (sx - inner_r, sy - inner_r))

        # ── Gun barrel ──
        gun_len = sc(self.radius + 10)
        gun_end_x = sx + math.cos(self.aim_angle) * gun_len
        gun_end_y = sy + math.sin(self.aim_angle) * gun_len
        pygame.draw.line(surface, body_color, (sx, sy),
                         (int(gun_end_x), int(gun_end_y)), max(1, sc(3)))

        # ── Crosshair dots ──
        for i in range(3):
            dist = sc(self.radius + 15 + i * 5)
            cx = sx + math.cos(self.aim_angle) * dist
            cy = sy + math.sin(self.aim_angle) * dist
            pygame.draw.circle(surface, NEON_CYAN, (int(cx), int(cy)), max(1, sc(2)))

    @property
    def alive(self):
        return self.hp > 0
