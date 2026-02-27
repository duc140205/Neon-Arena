"""
particles.py - Neon particle effects system with object pooling
Drawing uses camera.s() for native-resolution rendering.
"""

import pygame
import math
import random
from .settings import MAX_PARTICLES, NEON_CYAN, NEON_MAGENTA, NEON_PINK, NEON_YELLOW, NEON_ORANGE


class Particle:
    """A single particle with position, velocity, lifetime, and color."""

    __slots__ = ['x', 'y', 'vx', 'vy', 'lifetime', 'max_lifetime',
                 'color', 'size', 'active', 'fade', 'shrink']

    def __init__(self):
        self.active = False
        self.x = 0.0
        self.y = 0.0
        self.vx = 0.0
        self.vy = 0.0
        self.lifetime = 0.0
        self.max_lifetime = 1.0
        self.color = (255, 255, 255)
        self.size = 3.0
        self.fade = True
        self.shrink = True

    def init(self, x, y, vx, vy, lifetime, color, size, fade=True, shrink=True):
        self.active = True
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.lifetime = lifetime
        self.max_lifetime = lifetime
        self.color = color
        self.size = size
        self.fade = fade
        self.shrink = shrink

    def update(self, dt):
        if not self.active:
            return
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.lifetime -= dt
        if self.lifetime <= 0:
            self.active = False


class ParticleSystem:
    """Manages a pool of reusable particles for performance."""

    def __init__(self):
        self.pool = [Particle() for _ in range(MAX_PARTICLES)]
        self._next = 0

    def _get_particle(self):
        """Get the next available particle from the pool."""
        for i in range(MAX_PARTICLES):
            idx = (self._next + i) % MAX_PARTICLES
            if not self.pool[idx].active:
                self._next = (idx + 1) % MAX_PARTICLES
                return self.pool[idx]
        p = self.pool[self._next]
        self._next = (self._next + 1) % MAX_PARTICLES
        return p

    def emit(self, x, y, color, count=5, speed_range=(50, 200),
             lifetime_range=(0.3, 0.8), size_range=(2, 5), angle_range=None):
        """Emit particles in random directions."""
        for _ in range(count):
            p = self._get_particle()
            speed = random.uniform(*speed_range)
            if angle_range:
                angle = random.uniform(*angle_range)
            else:
                angle = random.uniform(0, math.pi * 2)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            lifetime = random.uniform(*lifetime_range)
            size = random.uniform(*size_range)
            p.init(x, y, vx, vy, lifetime, color, size)

    def emit_explosion(self, x, y, color=None, count=20):
        if color is None:
            colors = [NEON_CYAN, NEON_MAGENTA, NEON_PINK, NEON_YELLOW, NEON_ORANGE]
            for _ in range(count):
                c = random.choice(colors)
                self.emit(x, y, c, count=1, speed_range=(80, 350),
                          lifetime_range=(0.3, 1.0), size_range=(2, 6))
        else:
            self.emit(x, y, color, count=count, speed_range=(80, 350),
                      lifetime_range=(0.3, 1.0), size_range=(2, 6))

    def emit_trail(self, x, y, color, direction_angle, spread=0.5):
        self.emit(x, y, color, count=2, speed_range=(20, 80),
                  lifetime_range=(0.1, 0.3), size_range=(1, 3),
                  angle_range=(direction_angle - spread, direction_angle + spread))

    def emit_dash(self, x, y, color, count=15):
        self.emit(x, y, color, count=count, speed_range=(100, 300),
                  lifetime_range=(0.2, 0.5), size_range=(3, 7))

    def emit_xp(self, x, y):
        self.emit(x, y, NEON_CYAN, count=8, speed_range=(40, 120),
                  lifetime_range=(0.3, 0.6), size_range=(2, 4))

    def emit_levelup(self, x, y):
        for i in range(30):
            angle = (i / 30) * math.pi * 2
            p = self._get_particle()
            speed = random.uniform(150, 300)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            colors = [NEON_CYAN, NEON_MAGENTA, NEON_YELLOW]
            p.init(x, y, vx, vy, random.uniform(0.5, 1.0),
                   random.choice(colors), random.uniform(3, 6))

    def emit_powerup_spawn(self, x, y, color):
        """Ring of particles when a power-up appears."""
        for i in range(16):
            angle = (i / 16) * math.pi * 2
            p = self._get_particle()
            speed = random.uniform(60, 140)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            p.init(x, y, vx, vy, random.uniform(0.4, 0.8),
                   color, random.uniform(2, 5))

    def emit_powerup_collect(self, x, y, color):
        """High-density starburst when player collects a power-up."""
        # Inner dense burst
        for _ in range(25):
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(100, 350)
            p = self._get_particle()
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            p.init(x, y, vx, vy, random.uniform(0.3, 0.9),
                   color, random.uniform(3, 7))
        # Outer ring flash
        for i in range(12):
            angle = (i / 12) * math.pi * 2
            p = self._get_particle()
            speed = random.uniform(200, 400)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            bright_color = (
                min(255, color[0] + 80),
                min(255, color[1] + 80),
                min(255, color[2] + 80),
            )
            p.init(x, y, vx, vy, random.uniform(0.2, 0.5),
                   bright_color, random.uniform(2, 4), fade=True, shrink=False)

    def emit_speed_trail(self, x, y, move_angle):
        """Digital dust trail behind the player during speed buff."""
        # Emit behind the player (opposite of movement)
        back_angle = move_angle + math.pi
        for _ in range(2):
            offset_angle = back_angle + random.uniform(-0.6, 0.6)
            speed = random.uniform(20, 80)
            p = self._get_particle()
            vx = math.cos(offset_angle) * speed
            vy = math.sin(offset_angle) * speed
            # Small, dim particles for "digital dust"
            p.init(x + random.uniform(-5, 5), y + random.uniform(-5, 5),
                   vx, vy, random.uniform(0.15, 0.4),
                   NEON_MAGENTA, random.uniform(1.5, 3.5))

    def emit_barrel_sparks(self, x, y, barrel_angle):
        """Orange sparks at gun barrel tip — damage buff visual."""
        for _ in range(2):
            spark_angle = barrel_angle + random.uniform(-0.5, 0.5)
            speed = random.uniform(30, 100)
            p = self._get_particle()
            vx = math.cos(spark_angle) * speed
            vy = math.sin(spark_angle) * speed
            p.init(x, y, vx, vy, random.uniform(0.1, 0.25),
                   NEON_ORANGE, random.uniform(1, 3))

    def update(self, dt):
        for p in self.pool:
            if p.active:
                p.update(dt)

    def draw(self, surface, camera):
        """Draw all active particles with glow, scaled via camera.s()."""
        sw, sh = surface.get_size()
        sc = camera.s

        for p in self.pool:
            if not p.active:
                continue

            progress = max(0, p.lifetime / p.max_lifetime)

            if p.shrink:
                base_size = max(1, p.size * progress)
            else:
                base_size = max(1, p.size)

            current_size = sc(base_size)

            if p.fade:
                alpha = int(255 * progress)
            else:
                alpha = 255

            sx, sy = camera.apply(p.x, p.y)

            # Off-screen check
            margin = current_size + sc(4)
            if sx < -margin or sx > sw + margin:
                continue
            if sy < -margin or sy > sh + margin:
                continue

            # Draw glow
            if current_size >= 2:
                glow_size = current_size * 2
                glow_alpha = max(10, alpha // 3)
                glow_color = (
                    min(255, p.color[0]),
                    min(255, p.color[1]),
                    min(255, p.color[2]),
                )
                glow_surf = pygame.Surface((glow_size * 2, glow_size * 2), pygame.SRCALPHA)
                pygame.draw.circle(glow_surf, (*glow_color, glow_alpha),
                                   (glow_size, glow_size), glow_size)
                surface.blit(glow_surf, (sx - glow_size, sy - glow_size))

            # Draw core
            color_with_alpha = (*p.color, alpha)
            core_surf = pygame.Surface((current_size * 2, current_size * 2), pygame.SRCALPHA)
            pygame.draw.circle(core_surf, color_with_alpha,
                               (current_size, current_size), current_size)
            surface.blit(core_surf, (sx - current_size, sy - current_size))

    @property
    def active_count(self):
        return sum(1 for p in self.pool if p.active)
