"""
obstacles.py - Static arena obstacles and power-up pickups
Drawing uses camera.s() for native-resolution rendering.
"""

import pygame
import math
import random
from .settings import (
    ARENA_WIDTH, ARENA_HEIGHT,
    OBSTACLE_COUNT, OBSTACLE_MIN_SIZE, OBSTACLE_MAX_SIZE,
    OBSTACLE_COLOR, OBSTACLE_BORDER_COLOR, OBSTACLE_SAFE_RADIUS,
    POWERUP_RADIUS, POWERUP_LIFETIME, POWERUP_TYPES,
    POWERUP_SPAWN_INTERVAL, POWERUP_MAX_ACTIVE,
    NEON_CYAN, NEON_GREEN, NEON_YELLOW, NEON_MAGENTA, WHITE,
)


class Obstacle:
    """Static neon block that blocks movement and bullets."""

    def __init__(self, x, y, w, h):
        self.rect = pygame.Rect(x, y, w, h)
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        # Pick a random neon tint for variety
        self.border_color = OBSTACLE_BORDER_COLOR
        self.fill_color = OBSTACLE_COLOR

    def collides_circle(self, cx, cy, radius):
        """Check if a circle (player/enemy/bullet) collides with this rect."""
        # Find closest point on rect to circle center
        closest_x = max(self.rect.left, min(cx, self.rect.right))
        closest_y = max(self.rect.top, min(cy, self.rect.bottom))
        dx = cx - closest_x
        dy = cy - closest_y
        return (dx * dx + dy * dy) < (radius * radius)

    def push_circle_out(self, cx, cy, radius):
        """Push a circle out of this rectangle. Returns new (cx, cy)."""
        if not self.collides_circle(cx, cy, radius):
            return cx, cy

        # Find closest point
        closest_x = max(self.rect.left, min(cx, self.rect.right))
        closest_y = max(self.rect.top, min(cy, self.rect.bottom))
        dx = cx - closest_x
        dy = cy - closest_y
        dist = math.sqrt(dx * dx + dy * dy)

        if dist == 0:
            # Center is inside rect — push to nearest edge
            to_left = cx - self.rect.left
            to_right = self.rect.right - cx
            to_top = cy - self.rect.top
            to_bottom = self.rect.bottom - cy
            min_dist = min(to_left, to_right, to_top, to_bottom)
            if min_dist == to_left:
                return self.rect.left - radius, cy
            elif min_dist == to_right:
                return self.rect.right + radius, cy
            elif min_dist == to_top:
                return cx, self.rect.top - radius
            else:
                return cx, self.rect.bottom + radius

        # Push out along the line from closest point to center
        overlap = radius - dist
        nx = dx / dist
        ny = dy / dist
        return cx + nx * overlap, cy + ny * overlap

    def draw(self, surface, camera):
        """Draw with neon glow effect."""
        screen_rect = camera.apply_rect(self.rect)
        sc = camera.s

        # Off-screen check
        sw, sh = surface.get_size()
        if (screen_rect.right < -20 or screen_rect.left > sw + 20 or
                screen_rect.bottom < -20 or screen_rect.top > sh + 20):
            return

        # Fill
        fill_surf = pygame.Surface((screen_rect.width, screen_rect.height), pygame.SRCALPHA)
        fill_surf.fill((*self.fill_color, 180))
        surface.blit(fill_surf, screen_rect.topleft)

        # Border
        pygame.draw.rect(surface, self.border_color, screen_rect, max(1, sc(2)))

        # Inner glow line (top edge)
        glow_h = max(1, screen_rect.height // 6)
        glow_surf = pygame.Surface((screen_rect.width, glow_h), pygame.SRCALPHA)
        glow_surf.fill((*self.border_color, 30))
        surface.blit(glow_surf, screen_rect.topleft)


def generate_obstacles():
    """Generate random obstacles in the arena, avoiding the center spawn area."""
    obstacles = []
    center_x = ARENA_WIDTH / 2
    center_y = ARENA_HEIGHT / 2
    margin = 60  # keep obstacles away from arena edges

    for _ in range(OBSTACLE_COUNT * 3):  # extra attempts for placement
        if len(obstacles) >= OBSTACLE_COUNT:
            break

        w = random.randint(OBSTACLE_MIN_SIZE, OBSTACLE_MAX_SIZE)
        h = random.randint(OBSTACLE_MIN_SIZE, OBSTACLE_MAX_SIZE)
        x = random.randint(margin, ARENA_WIDTH - margin - w)
        y = random.randint(margin, ARENA_HEIGHT - margin - h)

        # Check distance from center (spawn area)
        ox = x + w / 2
        oy = y + h / 2
        dist = math.sqrt((ox - center_x) ** 2 + (oy - center_y) ** 2)
        if dist < OBSTACLE_SAFE_RADIUS:
            continue

        # Check overlap with existing obstacles (with padding)
        new_rect = pygame.Rect(x - 20, y - 20, w + 40, h + 40)
        overlap = False
        for obs in obstacles:
            if new_rect.colliderect(obs.rect):
                overlap = True
                break
        if overlap:
            continue

        obstacles.append(Obstacle(x, y, w, h))

    return obstacles


# ── Power-Ups ────────────────────────────────────────────

class PowerUp:
    """A pickup item that spawns in the arena and grants a temporary buff."""

    def __init__(self, x, y, powerup_type):
        self.pos_x = float(x)
        self.pos_y = float(y)
        self.radius = POWERUP_RADIUS
        self.type = powerup_type
        self.info = POWERUP_TYPES[powerup_type]
        self.color = self.info["color"]
        self.lifetime = POWERUP_LIFETIME
        self.alive = True
        self.bob_offset = random.uniform(0, math.pi * 2)
        self.just_spawned = True  # triggers spawn VFX once

    def update(self, dt):
        self.lifetime -= dt
        if self.lifetime <= 0:
            self.alive = False

    def collides_player(self, player_x, player_y, player_radius):
        dx = self.pos_x - player_x
        dy = self.pos_y - player_y
        dist = math.sqrt(dx * dx + dy * dy)
        return dist < self.radius + player_radius

    def draw(self, surface, camera):
        sx, sy = camera.apply(self.pos_x, self.pos_y)
        sc = camera.s

        # Off-screen check
        margin = sc(self.radius + 20)
        sw, sh = surface.get_size()
        if sx < -margin or sx > sw + margin or sy < -margin or sy > sh + margin:
            return

        # Bobbing animation
        bob = math.sin(pygame.time.get_ticks() * 0.005 + self.bob_offset) * sc(3)
        draw_y = sy + int(bob)

        r = sc(self.radius)

        # Outer glow (pulsing)
        pulse = 0.6 + 0.4 * math.sin(pygame.time.get_ticks() * 0.008 + self.bob_offset)
        glow_r = int(r * 2 * pulse)
        if glow_r > 0:
            glow_surf = pygame.Surface((glow_r * 2, glow_r * 2), pygame.SRCALPHA)
            pygame.draw.circle(glow_surf, (*self.color, 40),
                               (glow_r, glow_r), glow_r)
            surface.blit(glow_surf, (sx - glow_r, draw_y - glow_r))

        # Core circle
        pygame.draw.circle(surface, self.color, (sx, draw_y), r)
        pygame.draw.circle(surface, WHITE, (sx, draw_y), max(1, r // 2))

        # Despawn warning (flash when <3s)
        if self.lifetime < 3.0:
            if int(self.lifetime * 6) % 2 == 0:
                pygame.draw.circle(surface, WHITE, (sx, draw_y), r, max(1, sc(1)))


class PowerUpManager:
    """Manages spawning and lifetime of power-ups in the arena."""

    def __init__(self, obstacles, particle_system=None):
        self.powerups = []
        self.spawn_timer = POWERUP_SPAWN_INTERVAL * 0.5  # first spawn sooner
        self.obstacles = obstacles
        self.particles = particle_system

    def update(self, dt, player_x, player_y, player_radius):
        """Update all powerups. Returns list of (type, color) collected."""
        self.spawn_timer -= dt
        collected = []

        # Spawn new powerups
        if self.spawn_timer <= 0 and len(self.powerups) < POWERUP_MAX_ACTIVE:
            self.spawn_timer = POWERUP_SPAWN_INTERVAL
            self._spawn_powerup()

        # Update existing
        for pu in self.powerups[:]:
            # Fire spawn VFX once
            if pu.just_spawned and self.particles:
                self.particles.emit_powerup_spawn(pu.pos_x, pu.pos_y, pu.color)
                pu.just_spawned = False

            pu.update(dt)
            if not pu.alive:
                self.powerups.remove(pu)
                continue
            if pu.collides_player(player_x, player_y, player_radius):
                collected.append((pu.type, pu.color))
                # Collection VFX
                if self.particles:
                    self.particles.emit_powerup_collect(
                        pu.pos_x, pu.pos_y, pu.color)
                self.powerups.remove(pu)

        return collected

    def _spawn_powerup(self):
        """Spawn a weighted-random powerup at a valid position."""
        # Weighted selection
        types = list(POWERUP_TYPES.keys())
        weights = [POWERUP_TYPES[t]["weight"] for t in types]
        chosen = random.choices(types, weights=weights, k=1)[0]

        margin = 80
        for _ in range(30):
            x = random.uniform(margin, ARENA_WIDTH - margin)
            y = random.uniform(margin, ARENA_HEIGHT - margin)

            # Check obstacle overlap
            valid = True
            for obs in self.obstacles:
                if obs.collides_circle(x, y, POWERUP_RADIUS + 20):
                    valid = False
                    break
            if valid:
                self.powerups.append(PowerUp(x, y, chosen))
                return

    def draw(self, surface, camera):
        for pu in self.powerups:
            pu.draw(surface, camera)
