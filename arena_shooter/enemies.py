"""enemies.py - Enemy types: Chaser, Shooter, Tank, Boss, SniperBoss, SlimeBoss,
                       SuicideBomber, ShieldGuard
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
    NEON_RED, NEON_ORANGE, NEON_PURPLE, NEON_CYAN, NEON_YELLOW, NEON_MAGENTA, WHITE,
    NEON_GREEN, NEON_BLUE,
    ARENA_WIDTH, ARENA_HEIGHT,
    CHASER_BURST_CHANCE, CHASER_BURST_SPEED_MULT, CHASER_BURST_DURATION,
    SHOOTER_FAN_BULLET_COUNT, SHOOTER_FAN_SPREAD,
    TANK_SHIELD_COOLDOWN, TANK_SHIELD_DURATION, TANK_SHIELD_REDUCTION,
    BOSS_SPEED, BOSS_HP, BOSS_SIZE, BOSS_DAMAGE, BOSS_XP, BOSS_COLOR,
    BOSS_CHARGE_SPEED_MULT, BOSS_CHARGE_DURATION, BOSS_CHARGE_COOLDOWN,
    BOSS_SLAM_RADIUS, BOSS_SLAM_DAMAGE, BOSS_SLAM_COOLDOWN,
    BOSS_MINION_COUNT, BOSS_MINION_COOLDOWN,
    SNIPER_BOSS_SPEED, SNIPER_BOSS_HP, SNIPER_BOSS_SIZE, SNIPER_BOSS_DAMAGE,
    SNIPER_BOSS_XP, SNIPER_BOSS_COLOR, SNIPER_BOSS_PREFERRED_DIST,
    SNIPER_BOSS_FIRE_RATE, SNIPER_BOSS_BULLET_SPEED,
    SNIPER_BOSS_RING_COOLDOWN, SNIPER_BOSS_RING_BULLET_COUNT,
    SNIPER_BOSS_RING_BULLET_SPEED,
    SLIME_BOSS_SPEED, SLIME_BOSS_HP, SLIME_BOSS_SIZE, SLIME_BOSS_DAMAGE,
    SLIME_BOSS_XP, SLIME_BOSS_COLOR,
    SLIME_BOSS_TRAIL_DAMAGE, SLIME_BOSS_TRAIL_INTERVAL,
    SLIME_BOSS_TRAIL_LIFETIME, SLIME_BOSS_TRAIL_RADIUS,
    SLIME_BOSS_JUMP_COOLDOWN, SLIME_BOSS_JUMP_SPEED, SLIME_BOSS_JUMP_DURATION,
    SLIME_BOSS_SHOCKWAVE_RADIUS, SLIME_BOSS_SHOCKWAVE_DAMAGE,
    BOMBER_SPEED, BOMBER_HP, BOMBER_SIZE, BOMBER_DAMAGE, BOMBER_XP, BOMBER_COLOR,
    BOMBER_PRIME_RANGE, BOMBER_PRIME_DURATION, BOMBER_EXPLOSION_RADIUS,
    BOMBER_TURN_RATE,
    SHIELD_GUARD_SPEED, SHIELD_GUARD_HP, SHIELD_GUARD_SIZE, SHIELD_GUARD_DAMAGE,
    SHIELD_GUARD_XP, SHIELD_GUARD_COLOR, SHIELD_GUARD_ARC, SHIELD_GUARD_TURN_RATE,
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

        # Slow debuff (from Neon Pulse ultimate)
        self.slow_timer = 0.0
        self.slow_factor = 1.0  # 1.0 = normal speed

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

    def apply_slow(self, duration, factor):
        """Apply a slow debuff. Lower factor = slower."""
        self.slow_timer = max(self.slow_timer, duration)
        self.slow_factor = min(self.slow_factor, factor)

    def update(self, dt, player_x, player_y, enemy_bullets=None):
        self.flash_timer = max(0, self.flash_timer - dt)
        # Update slow debuff
        if self.slow_timer > 0:
            self.slow_timer -= dt
            if self.slow_timer <= 0:
                self.slow_timer = 0.0
                self.slow_factor = 1.0
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

        # Slow effect indicator (blue tint overlay)
        if self.slow_timer > 0:
            slow_r = sc(self.radius + 4)
            if slow_r > 0:
                slow_alpha = int(60 * min(1.0, self.slow_timer / 1.0))
                slow_surf = pygame.Surface((slow_r * 2, slow_r * 2), pygame.SRCALPHA)
                pygame.draw.circle(slow_surf, (*NEON_BLUE, slow_alpha),
                                   (slow_r, slow_r), slow_r)
                surface.blit(slow_surf, (sx - slow_r, sy - slow_r))

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
    """Rushes directly toward the player. Can burst-dash."""

    def __init__(self, x, y, hp_multiplier=1.0, speed_multiplier=1.0, damage_multiplier=1.0):
        super().__init__(
            x, y,
            speed=CHASER_SPEED * speed_multiplier,
            hp=int(CHASER_HP * hp_multiplier),
            size=CHASER_SIZE,
            damage=int(CHASER_DAMAGE * damage_multiplier),
            xp=CHASER_XP,
            color=CHASER_COLOR,
        )
        # Burst speed ability
        self.burst_timer = 0.0
        self.is_bursting = False
        self.base_speed = self.speed

    def update(self, dt, player_x, player_y, enemy_bullets=None):
        dx = player_x - self.pos_x
        dy = player_y - self.pos_y
        dist = math.sqrt(dx * dx + dy * dy)
        if dist > 0:
            dx /= dist
            dy /= dist

        # Burst speed logic
        if self.is_bursting:
            self.burst_timer -= dt
            if self.burst_timer <= 0:
                self.is_bursting = False
                self.speed = self.base_speed
        else:
            # Random chance to burst (only when close enough)
            if dist < 400 and random.random() < CHASER_BURST_CHANCE:
                self.is_bursting = True
                self.burst_timer = CHASER_BURST_DURATION
                self.speed = self.base_speed * CHASER_BURST_SPEED_MULT

        wobble = math.sin(pygame.time.get_ticks() * 0.005 + self.wobble_offset) * 0.3
        perp_x = -dy * wobble
        perp_y = dx * wobble

        move_speed = self.speed * self.slow_factor
        self.pos_x += (dx + perp_x) * move_speed * dt
        self.pos_y += (dy + perp_y) * move_speed * dt
        super().update(dt, player_x, player_y)

    def _draw_shape(self, surface, sx, sy, color, camera):
        """Draw as a triangle. Flashes white during burst."""
        r = camera.s(self.radius)
        draw_color = WHITE if self.is_bursting else color
        points = [
            (sx, sy - r),
            (sx + r, sy + r),
            (sx - r, sy + r),
        ]
        pygame.draw.polygon(surface, draw_color, points, max(1, camera.s(2)))

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
        alpha = 100 if self.is_bursting else 60
        pygame.draw.polygon(inner_surf, (*color, alpha), shifted)
        surface.blit(inner_surf, (sx - pad, sy - pad))


class Shooter(Enemy):
    """Keeps distance from the player and fires projectiles. Can fan-shot."""

    def __init__(self, x, y, hp_multiplier=1.0, speed_multiplier=1.0,
                 damage_multiplier=1.0, wave_num=1):
        super().__init__(
            x, y,
            speed=SHOOTER_SPEED * speed_multiplier,
            hp=int(SHOOTER_HP * hp_multiplier),
            size=SHOOTER_SIZE,
            damage=int(SHOOTER_DAMAGE * damage_multiplier),
            xp=SHOOTER_XP,
            color=SHOOTER_COLOR,
        )
        self.fire_timer = random.uniform(0, SHOOTER_FIRE_RATE)
        self.fire_rate = SHOOTER_FIRE_RATE
        self.preferred_dist = SHOOTER_PREFERRED_DIST
        # Fan shot unlocks based on wave number
        self.is_elite = wave_num >= 4

    def update(self, dt, player_x, player_y, enemy_bullets=None):
        dx = player_x - self.pos_x
        dy = player_y - self.pos_y
        dist = math.sqrt(dx * dx + dy * dy)
        if dist > 0:
            ndx = dx / dist
            ndy = dy / dist
        else:
            ndx, ndy = 0, 0

        effective_speed = self.speed * self.slow_factor
        if dist > self.preferred_dist + 30:
            self.pos_x += ndx * effective_speed * dt
            self.pos_y += ndy * effective_speed * dt
        elif dist < self.preferred_dist - 30:
            self.pos_x -= ndx * effective_speed * dt
            self.pos_y -= ndy * effective_speed * dt
        else:
            strafe = math.sin(pygame.time.get_ticks() * 0.002 + self.wobble_offset)
            self.pos_x += (-ndy * strafe) * effective_speed * dt
            self.pos_y += (ndx * strafe) * effective_speed * dt

        self.fire_timer -= dt
        if self.fire_timer <= 0 and enemy_bullets is not None:
            self.fire_timer = self.fire_rate
            angle = math.atan2(dy, dx)

            if self.is_elite:
                # Fan shot: fire multiple bullets in a spread
                count = SHOOTER_FAN_BULLET_COUNT
                spread = SHOOTER_FAN_SPREAD
                for i in range(count):
                    offset = spread * (i / (count - 1) - 0.5) if count > 1 else 0
                    bullet = EnemyBullet(
                        self.pos_x, self.pos_y, angle + offset,
                        SHOOTER_BULLET_SPEED, self.damage,
                    )
                    enemy_bullets.add(bullet)
            else:
                # Single shot
                bullet = EnemyBullet(
                    self.pos_x, self.pos_y, angle,
                    SHOOTER_BULLET_SPEED, self.damage,
                )
                enemy_bullets.add(bullet)

        super().update(dt, player_x, player_y)

    def _draw_shape(self, surface, sx, sy, color, camera):
        """Draw as a diamond/rhombus shape. Elite has pulsing ring."""
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

        # Elite indicator: outer pulsing ring
        if self.is_elite:
            pulse = int(5 * math.sin(pygame.time.get_ticks() * 0.008))
            elite_r = r + camera.s(4) + pulse
            elite_surf = pygame.Surface((elite_r * 2, elite_r * 2), pygame.SRCALPHA)
            pygame.draw.circle(elite_surf, (*NEON_ORANGE, 80),
                               (elite_r, elite_r), elite_r, max(1, camera.s(1)))
            surface.blit(elite_surf, (sx - elite_r, sy - elite_r))


class Tank(Enemy):
    """Slow, high-HP enemy that charges at the player. Has shield phase."""

    def __init__(self, x, y, hp_multiplier=1.0, speed_multiplier=1.0, damage_multiplier=1.0):
        super().__init__(
            x, y,
            speed=TANK_SPEED * speed_multiplier,
            hp=int(TANK_HP * hp_multiplier),
            size=TANK_SIZE,
            damage=int(TANK_DAMAGE * damage_multiplier),
            xp=TANK_XP,
            color=TANK_COLOR,
        )
        self.charge_timer = 3.0
        self.is_charging = False
        self.charge_duration = 1.0
        self.charge_vx = 0
        self.charge_vy = 0

        # Shield phase
        self.shield_cooldown_timer = TANK_SHIELD_COOLDOWN * random.uniform(0.5, 1.0)
        self.shield_timer = 0.0
        self.is_shielded = False

    def take_damage(self, amount, particle_system):
        """Override: reduce damage when shielded."""
        if self.is_shielded:
            amount = int(amount * (1.0 - TANK_SHIELD_REDUCTION))
            # Shield hit particles (cyan sparks)
            particle_system.emit(self.pos_x, self.pos_y, NEON_CYAN, count=4,
                                 speed_range=(60, 140), lifetime_range=(0.1, 0.25))
        return super().take_damage(amount, particle_system)

    def update(self, dt, player_x, player_y, enemy_bullets=None):
        dx = player_x - self.pos_x
        dy = player_y - self.pos_y
        dist = math.sqrt(dx * dx + dy * dy)

        # Shield phase logic
        if self.is_shielded:
            self.shield_timer -= dt
            if self.shield_timer <= 0:
                self.is_shielded = False
                self.shield_cooldown_timer = TANK_SHIELD_COOLDOWN
        else:
            self.shield_cooldown_timer -= dt
            if self.shield_cooldown_timer <= 0:
                self.is_shielded = True
                self.shield_timer = TANK_SHIELD_DURATION

        # Movement (charge or walk)
        effective_speed = self.speed * self.slow_factor
        if self.is_charging:
            self.charge_duration -= dt
            self.pos_x += self.charge_vx * self.slow_factor * dt
            self.pos_y += self.charge_vy * self.slow_factor * dt
            if self.charge_duration <= 0:
                self.is_charging = False
                self.charge_timer = 2.0 + random.uniform(0, 1.5)
        else:
            if dist > 0:
                ndx = dx / dist
                ndy = dy / dist
                self.pos_x += ndx * effective_speed * dt
                self.pos_y += ndy * effective_speed * dt

            self.charge_timer -= dt
            if self.charge_timer <= 0 and dist < 400:
                self.is_charging = True
                self.charge_duration = 0.6
                if dist > 0:
                    self.charge_vx = (dx / dist) * self.speed * 5
                    self.charge_vy = (dy / dist) * self.speed * 5

        super().update(dt, player_x, player_y)

    def _draw_shape(self, surface, sx, sy, color, camera):
        """Draw as a hexagon. Shield shown as cyan outer ring."""
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

        # Shield visual: pulsing cyan ring
        if self.is_shielded:
            pulse = int(3 * math.sin(pygame.time.get_ticks() * 0.01))
            shield_r = r + camera.s(6) + pulse
            shield_surf = pygame.Surface((shield_r * 2, shield_r * 2), pygame.SRCALPHA)
            pygame.draw.circle(shield_surf, (*NEON_CYAN, 100),
                               (shield_r, shield_r), shield_r, max(1, camera.s(2)))
            surface.blit(shield_surf, (sx - shield_r, sy - shield_r))


class Boss(Enemy):
    """Massive boss enemy with charge, AOE slam, and minion summon."""

    def __init__(self, x, y, hp_multiplier=1.0, speed_multiplier=1.0, damage_multiplier=1.0):
        super().__init__(
            x, y,
            speed=BOSS_SPEED * speed_multiplier,
            hp=int(BOSS_HP * hp_multiplier),
            size=BOSS_SIZE,
            damage=int(BOSS_DAMAGE * damage_multiplier),
            xp=BOSS_XP,
            color=BOSS_COLOR,
        )
        self.is_boss = True

        # Charge attack
        self.charge_timer = BOSS_CHARGE_COOLDOWN * 0.5
        self.charge_duration = 0.0
        self.is_charging = False
        self.charge_vx = 0.0
        self.charge_vy = 0.0
        self.base_speed = self.speed

        # AOE Slam
        self.slam_timer = BOSS_SLAM_COOLDOWN
        self.slam_active = False
        self.slam_anim_timer = 0.0
        self.slam_hit_player = False  # read by game.py

        # Minion summon
        self.minion_timer = BOSS_MINION_COOLDOWN * 0.6
        self.pending_minions = []  # [(x, y)] consumed by enemy_manager

    def update(self, dt, player_x, player_y, enemy_bullets=None):
        dx = player_x - self.pos_x
        dy = player_y - self.pos_y
        dist = math.sqrt(dx * dx + dy * dy)
        ndx = dx / dist if dist > 0 else 0
        ndy = dy / dist if dist > 0 else 0

        # ── Charge attack ──
        if self.is_charging:
            self.charge_duration -= dt
            self.pos_x += self.charge_vx * dt
            self.pos_y += self.charge_vy * dt
            if self.charge_duration <= 0:
                self.is_charging = False
                self.charge_timer = BOSS_CHARGE_COOLDOWN
        else:
            # Normal movement toward player
            self.pos_x += ndx * self.speed * dt
            self.pos_y += ndy * self.speed * dt

            self.charge_timer -= dt
            if self.charge_timer <= 0 and dist < 600:
                self.is_charging = True
                self.charge_duration = BOSS_CHARGE_DURATION
                self.charge_vx = ndx * self.base_speed * BOSS_CHARGE_SPEED_MULT
                self.charge_vy = ndy * self.base_speed * BOSS_CHARGE_SPEED_MULT

        # ── AOE Slam ──
        self.slam_timer -= dt
        self.slam_hit_player = False
        if self.slam_active:
            self.slam_anim_timer -= dt
            if self.slam_anim_timer <= 0:
                self.slam_active = False
        elif self.slam_timer <= 0 and dist < BOSS_SLAM_RADIUS + 50:
            self.slam_active = True
            self.slam_anim_timer = 0.4  # animation duration
            self.slam_timer = BOSS_SLAM_COOLDOWN
            if dist < BOSS_SLAM_RADIUS:
                self.slam_hit_player = True

        # ── Minion summon ──
        self.minion_timer -= dt
        if self.minion_timer <= 0:
            self.minion_timer = BOSS_MINION_COOLDOWN
            for i in range(BOSS_MINION_COUNT):
                angle = (i / BOSS_MINION_COUNT) * math.pi * 2
                mx = self.pos_x + math.cos(angle) * 80
                my = self.pos_y + math.sin(angle) * 80
                self.pending_minions.append((mx, my))

        super().update(dt, player_x, player_y)

    def _draw_shape(self, surface, sx, sy, color, camera):
        """Draw as a large octagon with inner glow and pulsing aura."""
        r = camera.s(self.radius)
        sc = camera.s

        # Pulsing outer aura
        pulse = 0.7 + 0.3 * math.sin(pygame.time.get_ticks() * 0.005)
        aura_r = int(r * 1.6 * pulse)
        if aura_r > 0:
            aura_surf = pygame.Surface((aura_r * 2, aura_r * 2), pygame.SRCALPHA)
            pygame.draw.circle(aura_surf, (*NEON_RED, 35),
                               (aura_r, aura_r), aura_r)
            surface.blit(aura_surf, (sx - aura_r, sy - aura_r))

        # Octagonal body
        points = []
        for i in range(8):
            angle = i * math.pi / 4 + pygame.time.get_ticks() * 0.0005
            px = sx + math.cos(angle) * r
            py = sy + math.sin(angle) * r
            points.append((int(px), int(py)))

        draw_color = WHITE if self.is_charging else color
        width = max(1, sc(3 if self.is_charging else 2))
        pygame.draw.polygon(surface, draw_color, points, width)

        # Inner fill
        pad = r + sc(2)
        inner_surf = pygame.Surface((pad * 2, pad * 2), pygame.SRCALPHA)
        shifted = [(p[0] - sx + pad, p[1] - sy + pad) for p in points]
        alpha = 100 if self.is_charging else 50
        pygame.draw.polygon(inner_surf, (*color, alpha), shifted)
        surface.blit(inner_surf, (sx - pad, sy - pad))

        # Core
        core_r = max(1, r // 3)
        pygame.draw.circle(surface, draw_color, (sx, sy), core_r)

        # Slam ring animation
        if self.slam_active:
            slam_progress = 1.0 - (self.slam_anim_timer / 0.4)
            slam_r = int(camera.s(BOSS_SLAM_RADIUS) * slam_progress)
            if slam_r > 0:
                slam_surf = pygame.Surface((slam_r * 2, slam_r * 2), pygame.SRCALPHA)
                ring_alpha = int(150 * (1.0 - slam_progress))
                pygame.draw.circle(slam_surf, (*NEON_YELLOW, ring_alpha),
                                   (slam_r, slam_r), slam_r, max(1, sc(3)))
                surface.blit(slam_surf, (sx - slam_r, sy - slam_r))


class SniperBoss(Enemy):
    """Long-range boss that fires high-speed laser shots and periodic ring attacks."""

    def __init__(self, x, y, hp_multiplier=1.0, speed_multiplier=1.0, damage_multiplier=1.0):
        super().__init__(
            x, y,
            speed=SNIPER_BOSS_SPEED * speed_multiplier,
            hp=int(SNIPER_BOSS_HP * hp_multiplier),
            size=SNIPER_BOSS_SIZE,
            damage=int(SNIPER_BOSS_DAMAGE * damage_multiplier),
            xp=SNIPER_BOSS_XP,
            color=SNIPER_BOSS_COLOR,
        )
        self.is_boss = True
        self.preferred_dist = SNIPER_BOSS_PREFERRED_DIST

        # Laser shot
        self.fire_timer = SNIPER_BOSS_FIRE_RATE * 0.5
        self.fire_rate = SNIPER_BOSS_FIRE_RATE

        # Ring of Death
        self.ring_timer = SNIPER_BOSS_RING_COOLDOWN
        self.ring_anim_timer = 0.0
        self.ring_active = False

        # Slam/minion compatibility fields (expected by game.py)
        self.slam_hit_player = False
        self.pending_minions = []

    def update(self, dt, player_x, player_y, enemy_bullets=None):
        dx = player_x - self.pos_x
        dy = player_y - self.pos_y
        dist = math.sqrt(dx * dx + dy * dy)
        ndx = dx / dist if dist > 0 else 0
        ndy = dy / dist if dist > 0 else 0

        self.slam_hit_player = False

        # Movement: try to maintain preferred distance
        if dist < self.preferred_dist - 50:
            # Too close — back away
            self.pos_x -= ndx * self.speed * 1.3 * dt
            self.pos_y -= ndy * self.speed * 1.3 * dt
        elif dist > self.preferred_dist + 80:
            # Too far — approach slowly
            self.pos_x += ndx * self.speed * 0.5 * dt
            self.pos_y += ndy * self.speed * 0.5 * dt
        else:
            # Strafe at ideal distance
            strafe = math.sin(pygame.time.get_ticks() * 0.002 + self.wobble_offset)
            self.pos_x += (-ndy * strafe) * self.speed * dt
            self.pos_y += (ndx * strafe) * self.speed * dt

        # Laser shot
        self.fire_timer -= dt
        if self.fire_timer <= 0 and enemy_bullets is not None:
            self.fire_timer = self.fire_rate
            angle = math.atan2(dy, dx)
            bullet = EnemyBullet(
                self.pos_x, self.pos_y, angle,
                SNIPER_BOSS_BULLET_SPEED, self.damage,
                color=NEON_CYAN, size=6,
            )
            enemy_bullets.add(bullet)

        # Ring of Death
        self.ring_timer -= dt
        if self.ring_active:
            self.ring_anim_timer -= dt
            if self.ring_anim_timer <= 0:
                self.ring_active = False
        elif self.ring_timer <= 0 and enemy_bullets is not None:
            self.ring_timer = SNIPER_BOSS_RING_COOLDOWN
            self.ring_active = True
            self.ring_anim_timer = 0.3
            # Fire bullets in a full circle
            for i in range(SNIPER_BOSS_RING_BULLET_COUNT):
                angle = (i / SNIPER_BOSS_RING_BULLET_COUNT) * math.pi * 2
                bullet = EnemyBullet(
                    self.pos_x, self.pos_y, angle,
                    SNIPER_BOSS_RING_BULLET_SPEED, self.damage,
                    color=NEON_CYAN, size=5,
                )
                enemy_bullets.add(bullet)

        super().update(dt, player_x, player_y)

    def _draw_shape(self, surface, sx, sy, color, camera):
        """Draw as a diamond/crosshair with a sniper reticle aesthetic."""
        r = camera.s(self.radius)
        sc = camera.s

        # Pulsing outer aura
        pulse = 0.7 + 0.3 * math.sin(pygame.time.get_ticks() * 0.006)
        aura_r = int(r * 1.5 * pulse)
        if aura_r > 0:
            aura_surf = pygame.Surface((aura_r * 2, aura_r * 2), pygame.SRCALPHA)
            pygame.draw.circle(aura_surf, (*NEON_CYAN, 30),
                               (aura_r, aura_r), aura_r)
            surface.blit(aura_surf, (sx - aura_r, sy - aura_r))

        # Diamond body
        points = [
            (sx, sy - r),
            (sx + r, sy),
            (sx, sy + r),
            (sx - r, sy),
        ]
        pygame.draw.polygon(surface, color, points, max(1, sc(2)))

        # Inner fill
        pad = r + sc(2)
        inner_surf = pygame.Surface((pad * 2, pad * 2), pygame.SRCALPHA)
        shifted = [(p[0] - sx + pad, p[1] - sy + pad) for p in points]
        pygame.draw.polygon(inner_surf, (*color, 50), shifted)
        surface.blit(inner_surf, (sx - pad, sy - pad))

        # Crosshair lines
        line_len = int(r * 0.7)
        line_w = max(1, sc(1))
        pygame.draw.line(surface, color, (sx - line_len, sy), (sx + line_len, sy), line_w)
        pygame.draw.line(surface, color, (sx, sy - line_len), (sx, sy + line_len), line_w)

        # Core dot
        core_r = max(1, r // 4)
        pygame.draw.circle(surface, WHITE, (sx, sy), core_r)

        # Ring of Death animation
        if self.ring_active:
            ring_progress = 1.0 - (self.ring_anim_timer / 0.3)
            ring_r = int(r * 2.5 * ring_progress)
            if ring_r > 0:
                ring_surf = pygame.Surface((ring_r * 2, ring_r * 2), pygame.SRCALPHA)
                ring_alpha = int(180 * (1.0 - ring_progress))
                pygame.draw.circle(ring_surf, (*NEON_CYAN, ring_alpha),
                                   (ring_r, ring_r), ring_r, max(1, sc(2)))
                surface.blit(ring_surf, (sx - ring_r, sy - ring_r))


class SlimeBoss(Enemy):
    """Area-denial boss that leaves toxic trail and jumps to create shockwaves."""

    def __init__(self, x, y, hp_multiplier=1.0, speed_multiplier=1.0, damage_multiplier=1.0):
        super().__init__(
            x, y,
            speed=SLIME_BOSS_SPEED * speed_multiplier,
            hp=int(SLIME_BOSS_HP * hp_multiplier),
            size=SLIME_BOSS_SIZE,
            damage=int(SLIME_BOSS_DAMAGE * damage_multiplier),
            xp=SLIME_BOSS_XP,
            color=SLIME_BOSS_COLOR,
        )
        self.is_boss = True

        # Toxic trail
        self.trail_timer = 0.0
        self.toxic_pools = []  # [(x, y, lifetime, damage, radius)] - managed by game.py

        # Jump attack
        self.jump_cooldown_timer = SLIME_BOSS_JUMP_COOLDOWN * 0.6
        self.jump_timer = 0.0
        self.is_jumping = False
        self.jump_vx = 0.0
        self.jump_vy = 0.0
        self.base_speed = self.speed

        # Shockwave signal (read by game.py)
        self.slam_hit_player = False
        self.shockwave_anim_timer = 0.0
        self.shockwave_active = False
        self.pending_minions = []

    def update(self, dt, player_x, player_y, enemy_bullets=None):
        dx = player_x - self.pos_x
        dy = player_y - self.pos_y
        dist = math.sqrt(dx * dx + dy * dy)
        ndx = dx / dist if dist > 0 else 0
        ndy = dy / dist if dist > 0 else 0

        self.slam_hit_player = False

        # Jump attack
        if self.is_jumping:
            self.jump_timer -= dt
            self.pos_x += self.jump_vx * dt
            self.pos_y += self.jump_vy * dt
            if self.jump_timer <= 0:
                self.is_jumping = False
                self.jump_cooldown_timer = SLIME_BOSS_JUMP_COOLDOWN
                # Landing shockwave
                self.shockwave_active = True
                self.shockwave_anim_timer = 0.4
                # Check if player is in shockwave range
                land_dx = player_x - self.pos_x
                land_dy = player_y - self.pos_y
                land_dist = math.sqrt(land_dx * land_dx + land_dy * land_dy)
                if land_dist < SLIME_BOSS_SHOCKWAVE_RADIUS:
                    self.slam_hit_player = True
        else:
            # Normal slow movement toward player
            self.pos_x += ndx * self.speed * dt
            self.pos_y += ndy * self.speed * dt

            # Jump cooldown
            self.jump_cooldown_timer -= dt
            if self.jump_cooldown_timer <= 0 and dist < 800:
                self.is_jumping = True
                self.jump_timer = SLIME_BOSS_JUMP_DURATION
                self.jump_vx = ndx * SLIME_BOSS_JUMP_SPEED
                self.jump_vy = ndy * SLIME_BOSS_JUMP_SPEED

        # Shockwave animation
        if self.shockwave_active:
            self.shockwave_anim_timer -= dt
            if self.shockwave_anim_timer <= 0:
                self.shockwave_active = False

        # Toxic trail: leave pools while moving (not during jump)
        if not self.is_jumping:
            self.trail_timer -= dt
            if self.trail_timer <= 0:
                self.trail_timer = SLIME_BOSS_TRAIL_INTERVAL
                self.toxic_pools.append((
                    self.pos_x, self.pos_y,
                    SLIME_BOSS_TRAIL_LIFETIME,
                    SLIME_BOSS_TRAIL_DAMAGE,
                    SLIME_BOSS_TRAIL_RADIUS,
                ))

        super().update(dt, player_x, player_y)

    def _draw_shape(self, surface, sx, sy, color, camera):
        """Draw as a blob/slime shape with dripping effect."""
        r = camera.s(self.radius)
        sc = camera.s

        # Pulsing aura (toxic glow)
        pulse = 0.6 + 0.4 * math.sin(pygame.time.get_ticks() * 0.004)
        aura_r = int(r * 1.6 * pulse)
        if aura_r > 0:
            aura_surf = pygame.Surface((aura_r * 2, aura_r * 2), pygame.SRCALPHA)
            pygame.draw.circle(aura_surf, (*NEON_GREEN, 35),
                               (aura_r, aura_r), aura_r)
            surface.blit(aura_surf, (sx - aura_r, sy - aura_r))

        # Main blob body — use a wobbly circle approximation
        t = pygame.time.get_ticks() * 0.003
        points = []
        num_pts = 12
        for i in range(num_pts):
            angle = (i / num_pts) * math.pi * 2
            wobble = 1.0 + 0.12 * math.sin(t + angle * 3)
            if self.is_jumping:
                wobble *= 0.85  # squash during jump
            px = sx + math.cos(angle) * r * wobble
            py = sy + math.sin(angle) * r * wobble
            points.append((int(px), int(py)))

        draw_color = WHITE if self.is_jumping else color
        pygame.draw.polygon(surface, draw_color, points, max(1, sc(2)))

        # Inner fill
        pad = r + sc(4)
        inner_surf = pygame.Surface((pad * 2, pad * 2), pygame.SRCALPHA)
        shifted = [(p[0] - sx + pad, p[1] - sy + pad) for p in points]
        alpha = 90 if self.is_jumping else 50
        pygame.draw.polygon(inner_surf, (*color, alpha), shifted)
        surface.blit(inner_surf, (sx - pad, sy - pad))

        # Eyes (two dots)
        eye_dist = max(1, r // 3)
        eye_r = max(1, r // 6)
        for sign in (-1, 1):
            ex = sx + sign * eye_dist
            ey = sy - eye_dist // 2
            pygame.draw.circle(surface, WHITE, (int(ex), int(ey)), eye_r)
            # Pupil
            pupil_r = max(1, eye_r // 2)
            pygame.draw.circle(surface, (20, 20, 20), (int(ex), int(ey)), pupil_r)

        # Shockwave ring animation
        if self.shockwave_active:
            sw_progress = 1.0 - (self.shockwave_anim_timer / 0.4)
            sw_r = int(camera.s(SLIME_BOSS_SHOCKWAVE_RADIUS) * sw_progress)
            if sw_r > 0:
                sw_surf = pygame.Surface((sw_r * 2, sw_r * 2), pygame.SRCALPHA)
                sw_alpha = int(150 * (1.0 - sw_progress))
                pygame.draw.circle(sw_surf, (*NEON_GREEN, sw_alpha),
                                   (sw_r, sw_r), sw_r, max(1, sc(3)))
                surface.blit(sw_surf, (sx - sw_r, sy - sw_r))


class SuicideBomber(Enemy):
    """High-speed fragile enemy that primes and explodes near the player."""

    def __init__(self, x, y, hp_multiplier=1.0, speed_multiplier=1.0, damage_multiplier=1.0):
        super().__init__(
            x, y,
            speed=BOMBER_SPEED * speed_multiplier,
            hp=int(BOMBER_HP * hp_multiplier),
            size=BOMBER_SIZE,
            damage=int(BOMBER_DAMAGE * damage_multiplier),
            xp=BOMBER_XP,
            color=BOMBER_COLOR,
        )
        self.is_priming = False
        self.prime_timer = 0.0
        # Facing angle (direction it's moving/looking)
        self.facing_angle = 0.0
        # Signals read by game.py
        self.exploded = False
        self.explosion_radius = BOMBER_EXPLOSION_RADIUS

    def update(self, dt, player_x, player_y, enemy_bullets=None):
        dx = player_x - self.pos_x
        dy = player_y - self.pos_y
        dist = math.sqrt(dx * dx + dy * dy)

        if self.is_priming:
            self.prime_timer -= dt
            if self.prime_timer <= 0:
                # Signal game.py to apply AOE — game.py will call kill()
                self.exploded = True
                return
        else:
            # Rush toward the player with limited turn rate
            if dist > 0:
                # Desired angle to player
                target_angle = math.atan2(dy, dx)
                
                # Calculate shortest angular distance (wrap to -pi..pi)
                angle_diff = (target_angle - self.facing_angle + math.pi) % (2 * math.pi) - math.pi
                
                # Limit rotation by turn rate
                max_turn = BOMBER_TURN_RATE * dt
                if abs(angle_diff) <= max_turn:
                    self.facing_angle = target_angle
                else:
                    self.facing_angle += max_turn if angle_diff > 0 else -max_turn
                
                # Move in current facing direction
                ndx = math.cos(self.facing_angle)
                ndy = math.sin(self.facing_angle)
                wobble = math.sin(pygame.time.get_ticks() * 0.007 + self.wobble_offset) * 0.25
                perp_x = -ndy * wobble
                perp_y = ndx * wobble
                self.pos_x += (ndx + perp_x) * self.speed * dt
                self.pos_y += (ndy + perp_y) * self.speed * dt

            # Start priming when close enough
            if dist < BOMBER_PRIME_RANGE:
                self.is_priming = True
                self.prime_timer = BOMBER_PRIME_DURATION

        super().update(dt, player_x, player_y)

    def _draw_shape(self, surface, sx, sy, color, camera):
        """Draw as a small circle with spikes. Flash red while priming."""
        r = camera.s(self.radius)
        sc = camera.s

        if self.is_priming:
            # Rapid flash between red and white
            flash = int(self.prime_timer * 16) % 2 == 0
            draw_color = WHITE if flash else NEON_RED
            # Pulsing priming glow
            prime_progress = 1.0 - (self.prime_timer / BOMBER_PRIME_DURATION)
            glow_r = int(r * (1.3 + 0.7 * prime_progress))
            if glow_r > 0:
                glow_surf = pygame.Surface((glow_r * 2, glow_r * 2), pygame.SRCALPHA)
                glow_alpha = int(60 + 120 * prime_progress)
                pygame.draw.circle(glow_surf, (*NEON_RED, glow_alpha),
                                   (glow_r, glow_r), glow_r)
                surface.blit(glow_surf, (sx - glow_r, sy - glow_r))
        else:
            draw_color = color

        # Core body
        pygame.draw.circle(surface, draw_color, (sx, sy), r, max(1, sc(2)))

        # Inner fill
        inner_r = r - sc(2)
        if inner_r > 0:
            inner_surf = pygame.Surface((inner_r * 2, inner_r * 2), pygame.SRCALPHA)
            pygame.draw.circle(inner_surf, (*color, 70), (inner_r, inner_r), inner_r)
            surface.blit(inner_surf, (sx - inner_r, sy - inner_r))

        # Spikes (4 pointed projections)
        spike_len = r + sc(6)
        for i in range(4):
            angle = i * math.pi / 2 + pygame.time.get_ticks() * 0.005
            tip_x = sx + math.cos(angle) * spike_len
            tip_y = sy + math.sin(angle) * spike_len
            pygame.draw.line(surface, draw_color, (sx, sy),
                             (int(tip_x), int(tip_y)), max(1, sc(1)))

        # Danger icon (exclamation mark when priming)
        if self.is_priming:
            exc = "!"
            try:
                font = pygame.font.SysFont("consolas", max(8, sc(14)), bold=True)
            except Exception:
                font = pygame.font.Font(None, max(8, sc(14)))
            exc_surf = font.render(exc, True, NEON_RED)
            exc_rect = exc_surf.get_rect(center=(sx, sy - r - sc(10)))
            surface.blit(exc_surf, exc_rect)


class ShieldGuard(Enemy):
    """Slow tank with a directional front shield immune to frontal bullets."""

    def __init__(self, x, y, hp_multiplier=1.0, speed_multiplier=1.0, damage_multiplier=1.0):
        super().__init__(
            x, y,
            speed=SHIELD_GUARD_SPEED * speed_multiplier,
            hp=int(SHIELD_GUARD_HP * hp_multiplier),
            size=SHIELD_GUARD_SIZE,
            damage=int(SHIELD_GUARD_DAMAGE * damage_multiplier),
            xp=SHIELD_GUARD_XP,
            color=SHIELD_GUARD_COLOR,
        )
        # The angle the guard is facing (toward the player)
        self.facing_angle = 0.0
        self.shield_arc = SHIELD_GUARD_ARC  # full arc width in radians

    def is_bullet_shielded(self, bullet_angle):
        """Return True if a bullet coming from bullet_angle hits the front shield.

        bullet_angle is the angle FROM the guard center TO the bullet,
        i.e. the direction the bullet is located relative to the guard.
        The shield blocks bullets arriving from the guard facing direction.
        """
        # Angle difference (wrap to -pi..pi)
        diff = (bullet_angle - self.facing_angle + math.pi) % (2 * math.pi) - math.pi
        return abs(diff) <= self.shield_arc / 2

    def take_damage(self, amount, particle_system, from_angle=None):
        """Override: if from_angle is provided and shielded, block damage."""
        if from_angle is not None and self.is_bullet_shielded(from_angle):
            # Shield sparks — bullet deflected
            particle_system.emit(self.pos_x, self.pos_y, NEON_CYAN, count=6,
                                 speed_range=(80, 200), lifetime_range=(0.1, 0.25))
            return False
        return super().take_damage(amount, particle_system)

    def update(self, dt, player_x, player_y, enemy_bullets=None):
        dx = player_x - self.pos_x
        dy = player_y - self.pos_y
        dist = math.sqrt(dx * dx + dy * dy)

        if dist > 0:
            # Desired angle to player
            target_angle = math.atan2(dy, dx)
            
            # Calculate shortest angular distance (wrap to -pi..pi)
            angle_diff = (target_angle - self.facing_angle + math.pi) % (2 * math.pi) - math.pi
            
            # Limit rotation by turn rate
            max_turn = SHIELD_GUARD_TURN_RATE * dt
            if abs(angle_diff) <= max_turn:
                self.facing_angle = target_angle
            else:
                self.facing_angle += max_turn if angle_diff > 0 else -max_turn
            
            # Move in current facing direction
            ndx = math.cos(self.facing_angle)
            ndy = math.sin(self.facing_angle)
            self.pos_x += ndx * self.speed * dt
            self.pos_y += ndy * self.speed * dt

        super().update(dt, player_x, player_y)

    def _draw_shape(self, surface, sx, sy, color, camera):
        """Draw as a hexagonal body with a visible shield arc on the front."""
        r = camera.s(self.radius)
        sc = camera.s

        # Body: hexagon
        points = []
        for i in range(6):
            angle = self.facing_angle + math.pi / 6 + i * math.pi / 3
            px = sx + math.cos(angle) * r
            py = sy + math.sin(angle) * r
            points.append((int(px), int(py)))
        pygame.draw.polygon(surface, color, points, max(1, sc(2)))

        # Inner fill
        pad = r + sc(2)
        inner_surf = pygame.Surface((pad * 2, pad * 2), pygame.SRCALPHA)
        shifted = [(p[0] - sx + pad, p[1] - sy + pad) for p in points]
        pygame.draw.polygon(inner_surf, (*color, 50), shifted)
        surface.blit(inner_surf, (sx - pad, sy - pad))

        # Shield arc (thick bright arc on the front)
        shield_r = r + sc(8)
        half_arc = self.shield_arc / 2
        num_segs = 12
        # Draw as a series of connected line segments
        arc_points = []
        for i in range(num_segs + 1):
            frac = i / num_segs
            angle = self.facing_angle - half_arc + frac * self.shield_arc
            ax = sx + math.cos(angle) * shield_r
            ay = sy + math.sin(angle) * shield_r
            arc_points.append((int(ax), int(ay)))

        # Pulsing shield alpha
        pulse = 0.6 + 0.4 * math.sin(pygame.time.get_ticks() * 0.006)
        shield_alpha = int(180 * pulse)

        if len(arc_points) >= 2:
            # Draw thick arc segments
            line_w = max(2, sc(4))
            shield_line_surf = pygame.Surface(
                (shield_r * 2 + sc(12), shield_r * 2 + sc(12)), pygame.SRCALPHA)
            offset = shield_r + sc(6)
            shifted_arc = [(p[0] - sx + offset, p[1] - sy + offset) for p in arc_points]
            pygame.draw.lines(shield_line_surf, (*NEON_CYAN, shield_alpha),
                              False, shifted_arc, line_w)
            surface.blit(shield_line_surf, (sx - offset, sy - offset))

        # Center eye
        pygame.draw.circle(surface, color, (sx, sy), max(1, r // 3))
