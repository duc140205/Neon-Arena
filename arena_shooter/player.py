"""
player.py - Player sprite with WASD movement, mouse aiming, shooting, and dash
All drawing uses camera.s() for native-resolution rendering.
"""

import pygame
import math
from .settings import (
    PLAYER_SPEED, PLAYER_SIZE, PLAYER_MAX_HP, PLAYER_FIRE_RATE,
    PLAYER_BULLET_SPEED, PLAYER_BULLET_DAMAGE, PLAYER_BULLET_SIZE,
    DASH_SPEED, DASH_DURATION, DASH_COOLDOWN, DASH_PARTICLES, DASH_DECAY_DURATION,
    NEON_CYAN, NEON_MAGENTA, NEON_PINK, NEON_ORANGE, NEON_YELLOW, NEON_BLUE, WHITE,
    ARENA_WIDTH, ARENA_HEIGHT,
    BASE_XP_REQUIRED, XP_SCALE_FACTOR,
    GHOST_TRAIL_INTERVAL, GHOST_TRAIL_LIFETIME, GHOST_TRAIL_RADIUS,
    GHOST_TRAIL_DAMAGE,
    SHIELD_DURATION, DOUBLE_DAMAGE_DURATION,
    SPEED_BOOST_DURATION, SPEED_BOOST_MULT,
    REFLEX_FIRE_RATE_MULT, REFLEX_DURATION,
    SHOTGUN_CONE_ANGLE,
    RAILGUN_DURATION, RAILGUN_BULLET_SPEED, RAILGUN_DAMAGE_MULT, RAILGUN_SIZE,
)
from .projectiles import PlayerBullet, RailgunBullet


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

        # Post-dash speed decay — velocity bleed after the dash window closes
        self.dash_decay_vx = 0.0
        self.dash_decay_vy = 0.0
        self.dash_decay_timer = 0.0

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
            "giant_growth": 0, "multi_barrel": 0,
            "ghost_dash": 0, "dash_shockwave": 0, "reflex_dash": 0,
        }

        # Invincibility
        self.invincible_timer = 0.0
        self.invincible_duration = 1.0
        self.flash_timer = 0.0

        # Ghost Dash trail
        self.ghost_trail_timer = 0.0
        self.ghost_trail_positions = []  # [(x, y, lifetime)] - managed by game.py

        # Dash-end signals (read by game.py after dash ends)
        self.dash_ended_this_frame = False
        self.dash_end_x = 0.0
        self.dash_end_y = 0.0
        self.bullets_phased = 0  # count of bullets dashed through

        # Power-up buffs
        self.shield_timer = 0.0       # seconds of shield remaining
        self.double_damage_timer = 0.0
        self.speed_boost_timer = 0.0
        self.base_fire_rate = PLAYER_FIRE_RATE
        self.reflex_timer = 0.0       # temporary fire rate buff

        # Railgun power-up buff
        self.railgun_timer = 0.0      # seconds of railgun mode remaining

        # Shooting state flag (cleared when focus is lost)
        self.is_shooting = False

    def take_damage(self, amount):
        if self.invincible_timer > 0 or self.is_dashing:
            return False
        if self.shield_timer > 0:
            # Shield absorbs the hit
            self.shield_timer = max(0, self.shield_timer - 1.0)
            self.particles.emit(self.pos_x, self.pos_y, NEON_CYAN, count=8,
                                speed_range=(80, 200), lifetime_range=(0.2, 0.4))
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

    @property
    def barrel_count(self):
        """Number of bullets fired per shot (1 + multi_barrel level)."""
        return 1 + self.upgrade_levels.get("multi_barrel", 0)

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
        elif upgrade_key == "giant_growth":
            # Bigger target, but tankier and harder-hitting
            self.radius += 5
            self.max_hp += 50
            self.hp = min(self.max_hp, self.hp + 50)
            self.bullet_damage *= 1.30
            # Rebuild sprite rect for new size
            self.image = pygame.Surface(
                (self.radius * 2 + 4, self.radius * 2 + 4), pygame.SRCALPHA)
            self.rect = self.image.get_rect(center=(int(self.pos_x), int(self.pos_y)))
        # multi_barrel, ghost_dash, dash_shockwave, reflex_dash:
        # Handled by gameplay logic, no stat changes needed here

    def apply_powerup(self, powerup_type):
        """Apply a collected power-up buff."""
        if powerup_type == "health":
            heal = min(40, self.max_hp - self.hp)
            self.hp += heal
            self.particles.emit(self.pos_x, self.pos_y, NEON_CYAN, count=12,
                                speed_range=(40, 120), lifetime_range=(0.3, 0.6))
        elif powerup_type == "shield":
            self.shield_timer = SHIELD_DURATION
        elif powerup_type == "double_damage":
            self.double_damage_timer = DOUBLE_DAMAGE_DURATION
        elif powerup_type == "speed_boost":
            self.speed_boost_timer = SPEED_BOOST_DURATION
        elif powerup_type == "railgun":
            self.railgun_timer = RAILGUN_DURATION

    def update(self, dt, mouse_screen_pos, camera):
        self.fire_timer = max(0, self.fire_timer - dt)
        self.invincible_timer = max(0, self.invincible_timer - dt)
        self.flash_timer = max(0, self.flash_timer - dt)
        self.dash_cooldown_timer = max(0, self.dash_cooldown_timer - dt)
        self.shield_timer = max(0, self.shield_timer - dt)
        self.double_damage_timer = max(0, self.double_damage_timer - dt)
        self.speed_boost_timer = max(0, self.speed_boost_timer - dt)
        self.reflex_timer = max(0, self.reflex_timer - dt)
        self.railgun_timer = max(0, self.railgun_timer - dt)
        self.dash_ended_this_frame = False

        keys = pygame.key.get_pressed()

        # Resolve mouse world position early — needed for dash direction & aiming
        mouse_world_x, mouse_world_y = camera.world_pos(*mouse_screen_pos)
        self.aim_angle = math.atan2(mouse_world_y - self.pos_y, mouse_world_x - self.pos_x)

        if self.is_dashing:
            self.dash_timer -= dt
            self.pos_x += self.dash_vx * dt
            self.pos_y += self.dash_vy * dt
            if int(self.dash_timer * 60) % 2 == 0:
                self.particles.emit(self.pos_x, self.pos_y, NEON_MAGENTA, count=3,
                                    speed_range=(30, 100), lifetime_range=(0.15, 0.35),
                                    size_range=(3, 6))

            # Ghost Dash: leave fire trail positions
            if self.upgrade_levels.get("ghost_dash", 0) > 0:
                self.ghost_trail_timer -= dt
                if self.ghost_trail_timer <= 0:
                    self.ghost_trail_timer = GHOST_TRAIL_INTERVAL
                    level = self.upgrade_levels["ghost_dash"]
                    self.ghost_trail_positions.append((
                        self.pos_x, self.pos_y,
                        GHOST_TRAIL_LIFETIME * (1.0 + 0.3 * (level - 1)),
                        GHOST_TRAIL_DAMAGE * level,
                        GHOST_TRAIL_RADIUS + 4 * (level - 1),
                    ))
                    self.particles.emit(self.pos_x, self.pos_y, NEON_ORANGE, count=2,
                                        speed_range=(10, 40), lifetime_range=(0.2, 0.5),
                                        size_range=(3, 7))

            if self.dash_timer <= 0:
                self.is_dashing = False
                self.dash_ended_this_frame = True
                self.dash_end_x = self.pos_x
                self.dash_end_y = self.pos_y
                # Kick off momentum decay — carry dash velocity forward briefly
                self.dash_decay_vx = self.dash_vx
                self.dash_decay_vy = self.dash_vy
                self.dash_decay_timer = DASH_DECAY_DURATION
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

            # Apply lingering momentum from the previous dash (linear decay to 0)
            if self.dash_decay_timer > 0:
                self.dash_decay_timer = max(0.0, self.dash_decay_timer - dt)
                scale = self.dash_decay_timer / DASH_DECAY_DURATION
                self.pos_x += self.dash_decay_vx * scale * dt
                self.pos_y += self.dash_decay_vy * scale * dt

            if keys[pygame.K_SPACE] and self.dash_cooldown_timer <= 0:
                # Direction: movement keys take priority; fall back to mouse cursor
                if dx != 0 or dy != 0:
                    dir_x, dir_y = dx, dy   # already normalised
                else:
                    mdx = mouse_world_x - self.pos_x
                    mdy = mouse_world_y - self.pos_y
                    dist = math.sqrt(mdx * mdx + mdy * mdy)
                    if dist > 1e-6:
                        dir_x, dir_y = mdx / dist, mdy / dist
                    else:
                        dir_x = math.cos(self.aim_angle)
                        dir_y = math.sin(self.aim_angle)
                self.is_dashing = True
                self.dash_timer = self.dash_duration
                self.dash_cooldown_timer = self.dash_cooldown
                self.dash_vx = dir_x * self.dash_speed
                self.dash_vy = dir_y * self.dash_speed
                # Cancel any in-flight decay so old momentum doesn't add to the new dash
                self.dash_decay_timer = 0.0
                self.particles.emit_dash(self.pos_x, self.pos_y, NEON_MAGENTA, DASH_PARTICLES)

        self.pos_x = max(self.radius, min(ARENA_WIDTH - self.radius, self.pos_x))
        self.pos_y = max(self.radius, min(ARENA_HEIGHT - self.radius, self.pos_y))
        self.rect.centerx = int(self.pos_x)
        self.rect.centery = int(self.pos_y)
        # (aim_angle already computed above before the dash/move block)

    def try_shoot(self, bullet_group):
        # Only read mouse buttons when the OS cursor is inside our window.
        # pygame.mouse.get_focused() returns False the instant an overlay
        # (e.g. Win+Shift+S snipping tool) steals focus, so this is the last
        # line of defence against stale button states causing a crash.
        if not pygame.mouse.get_focused():
            self.is_shooting = False
            return False

        mouse_buttons = pygame.mouse.get_pressed()
        self.is_shooting = bool(mouse_buttons[0])
        # Effective fire rate (with reflex buff)
        effective_fire_rate = self.fire_rate
        if self.reflex_timer > 0:
            effective_fire_rate *= REFLEX_FIRE_RATE_MULT

        if mouse_buttons[0] and self.fire_timer <= 0 and not self.is_dashing:
            self.fire_timer = effective_fire_rate
            gun_dist = self.radius + 8
            count = self.barrel_count

            # Double damage buff
            dmg = self.bullet_damage
            if self.double_damage_timer > 0:
                dmg *= 2

            # --- Determine bullet angles ---
            if count == 1:
                angles = [self.aim_angle]
            else:
                # Forward-facing cone: center shot always fires,
                # extra bullets spread symmetrically in the cone.
                cone = SHOTGUN_CONE_ANGLE
                angles = [self.aim_angle]          # center barrel always fires
                n_extra = count - 1
                max_levels = (n_extra + 1) // 2    # unique spread distances
                for lvl in range(1, max_levels + 1):
                    spread = cone * lvl / max_levels
                    angles.append(self.aim_angle + spread)
                    if len(angles) < count:
                        angles.append(self.aim_angle - spread)

            # --- Choose bullet type ---
            use_railgun = self.railgun_timer > 0

            if use_railgun:
                bullet_color = NEON_BLUE
                rail_dmg = dmg * RAILGUN_DAMAGE_MULT
                for angle in angles:
                    bx = self.pos_x + math.cos(angle) * gun_dist
                    by = self.pos_y + math.sin(angle) * gun_dist
                    bullet = RailgunBullet(
                        bx, by, angle,
                        RAILGUN_BULLET_SPEED, rail_dmg,
                        color=bullet_color,
                        size=RAILGUN_SIZE,
                    )
                    bullet_group.add(bullet)
                    self.particles.emit(bx, by, bullet_color, count=4,
                                        speed_range=(80, 200), lifetime_range=(0.1, 0.25),
                                        size_range=(2, 5),
                                        angle_range=(angle - 0.3, angle + 0.3))
            else:
                bullet_color = NEON_YELLOW if self.double_damage_timer > 0 else NEON_CYAN
                for angle in angles:
                    bx = self.pos_x + math.cos(angle) * gun_dist
                    by = self.pos_y + math.sin(angle) * gun_dist
                    bullet = PlayerBullet(bx, by, angle,
                                          self.bullet_speed, dmg,
                                          color=bullet_color,
                                          size=self.bullet_size)
                    bullet_group.add(bullet)
                    self.particles.emit(bx, by, bullet_color, count=3,
                                        speed_range=(50, 150), lifetime_range=(0.1, 0.2),
                                        size_range=(2, 4),
                                        angle_range=(angle - 0.3, angle + 0.3))
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

        # ── Buff indicators ──
        # Shield: hexagonal holographic outline
        if self.shield_timer > 0:
            pulse = 0.6 + 0.4 * math.sin(pygame.time.get_ticks() * 0.008)
            shield_r = r + sc(10)
            rot = pygame.time.get_ticks() * 0.001  # slow rotation
            if shield_r > 2:
                shield_surf = pygame.Surface(
                    (shield_r * 2 + 4, shield_r * 2 + 4), pygame.SRCALPHA)
                cx_s, cy_s = shield_r + 2, shield_r + 2
                # Outer hex
                hex_pts = []
                for i in range(6):
                    angle = rot + i * math.pi / 3
                    hx = cx_s + math.cos(angle) * shield_r
                    hy = cy_s + math.sin(angle) * shield_r
                    hex_pts.append((int(hx), int(hy)))
                alpha_outer = int(120 * pulse)
                pygame.draw.polygon(shield_surf,
                                    (*NEON_CYAN, alpha_outer),
                                    hex_pts, max(1, sc(2)))
                # Inner hex (smaller, dimmer)
                inner_hex = []
                for i in range(6):
                    angle = rot + math.pi / 6 + i * math.pi / 3
                    hx = cx_s + math.cos(angle) * (shield_r * 0.7)
                    hy = cy_s + math.sin(angle) * (shield_r * 0.7)
                    inner_hex.append((int(hx), int(hy)))
                alpha_inner = int(60 * pulse)
                pygame.draw.polygon(shield_surf,
                                    (*NEON_CYAN, alpha_inner),
                                    inner_hex, max(1, sc(1)))
                surface.blit(shield_surf, (sx - cx_s, sy - cy_s))

        # Double damage glow
        if self.double_damage_timer > 0:
            dmg_r = r + sc(5)
            if dmg_r > 0:
                dmg_surf = pygame.Surface((dmg_r * 2, dmg_r * 2), pygame.SRCALPHA)
                pygame.draw.circle(dmg_surf, (*NEON_YELLOW, 50),
                                   (dmg_r, dmg_r), dmg_r)
                surface.blit(dmg_surf, (sx - dmg_r, sy - dmg_r))

        # Speed boost lines
        if self.speed_boost_timer > 0:
            for i in range(3):
                trail_dist = sc(self.radius + 8 + i * 6)
                t_angle = self.aim_angle + math.pi + (i - 1) * 0.3
                lx = sx + math.cos(t_angle) * trail_dist
                ly = sy + math.sin(t_angle) * trail_dist
                lx2 = sx + math.cos(t_angle) * (trail_dist + sc(8))
                ly2 = sy + math.sin(t_angle) * (trail_dist + sc(8))
                pygame.draw.line(surface, NEON_MAGENTA,
                                 (int(lx), int(ly)),
                                 (int(lx2), int(ly2)), max(1, sc(2)))

        # Reflex buff aura
        if self.reflex_timer > 0:
            ref_alpha = int(60 * abs(math.sin(pygame.time.get_ticks() * 0.012)))
            ref_r = r + sc(12)
            if ref_r > 0:
                ref_surf = pygame.Surface((ref_r * 2, ref_r * 2), pygame.SRCALPHA)
                pygame.draw.circle(ref_surf, (220, 230, 255, ref_alpha),
                                   (ref_r, ref_r), ref_r, max(1, sc(1)))
                surface.blit(ref_surf, (sx - ref_r, sy - ref_r))

    @property
    def alive(self):
        return self.hp > 0
