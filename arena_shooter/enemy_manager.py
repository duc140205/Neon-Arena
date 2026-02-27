"""
enemy_manager.py - Wave spawning and difficulty scaling
"""

import random
import math
from .enemies import Chaser, Shooter, Tank
from .settings import (
    ARENA_WIDTH, ARENA_HEIGHT, SPAWN_MARGIN, SPAWN_MIN_DIST,
    WAVE_BREAK_TIME, SCREEN_WIDTH, SCREEN_HEIGHT,
    DIFFICULTY_HP_PER_LEVEL, DIFFICULTY_SPEED_PER_LEVEL,
    DIFFICULTY_DAMAGE_PER_LEVEL,
)


class WaveDefinition:
    """Defines a single wave's enemy composition."""

    def __init__(self, chasers=0, shooters=0, tanks=0,
                 hp_mult=1.0, speed_mult=1.0, damage_mult=1.0):
        self.chasers = chasers
        self.shooters = shooters
        self.tanks = tanks
        self.hp_mult = hp_mult
        self.speed_mult = speed_mult
        self.damage_mult = damage_mult

    @property
    def total(self):
        return self.chasers + self.shooters + self.tanks


class EnemyManager:
    """Manages wave-based enemy spawning with progressive difficulty."""

    def __init__(self):
        self.wave = 0
        self.wave_active = False
        self.wave_timer = 2.0  # initial delay before first wave
        self.enemies_alive = 0
        self.total_enemies_killed = 0
        self.wave_announcement_timer = 0.0

        # Difficulty factor increases with player level
        self.difficulty_factor = 1.0

    def set_difficulty(self, player_level):
        """Update difficulty based on player level.

        Called by game.py whenever the player levels up.
        Scales enemy HP, speed, and damage multiplicatively.
        """
        lvl = player_level - 1  # level 1 = no bonus
        self.difficulty_factor = 1.0 + lvl * 0.05  # ~5% total per level

    def _generate_wave(self, wave_num):
        """Generate a wave definition based on wave number."""
        # Base counts that scale with wave number
        chasers = 3 + wave_num * 2
        shooters = max(0, wave_num - 1)
        tanks = max(0, (wave_num - 3) // 2)

        # Cap individual counts for sanity
        chasers = min(chasers, 20)
        shooters = min(shooters, 10)
        tanks = min(tanks, 5)

        # Wave-based scaling
        wave_hp = 1.0 + (wave_num - 1) * 0.1       # +10% HP per wave
        wave_speed = 1.0 + (wave_num - 1) * 0.03    # +3% speed per wave
        wave_damage = 1.0 + (wave_num - 1) * 0.05   # +5% damage per wave

        # Apply player-level difficulty on top
        df = self.difficulty_factor
        hp_mult = wave_hp * (1.0 + (df - 1.0) * DIFFICULTY_HP_PER_LEVEL / 0.05)
        speed_mult = wave_speed * (1.0 + (df - 1.0) * DIFFICULTY_SPEED_PER_LEVEL / 0.05)
        damage_mult = wave_damage * (1.0 + (df - 1.0) * DIFFICULTY_DAMAGE_PER_LEVEL / 0.05)

        return WaveDefinition(chasers, shooters, tanks,
                              hp_mult, speed_mult, damage_mult)

    def _get_spawn_pos(self, player_x, player_y, camera_rect):
        """Get a valid spawn position outside the camera view but inside arena."""
        for _ in range(50):
            # Spawn at edges of camera view or further
            side = random.randint(0, 3)
            if side == 0:  # top
                x = random.uniform(camera_rect.left - SPAWN_MARGIN,
                                   camera_rect.right + SPAWN_MARGIN)
                y = camera_rect.top - random.uniform(50, SPAWN_MARGIN)
            elif side == 1:  # bottom
                x = random.uniform(camera_rect.left - SPAWN_MARGIN,
                                   camera_rect.right + SPAWN_MARGIN)
                y = camera_rect.bottom + random.uniform(50, SPAWN_MARGIN)
            elif side == 2:  # left
                x = camera_rect.left - random.uniform(50, SPAWN_MARGIN)
                y = random.uniform(camera_rect.top - SPAWN_MARGIN,
                                   camera_rect.bottom + SPAWN_MARGIN)
            else:  # right
                x = camera_rect.right + random.uniform(50, SPAWN_MARGIN)
                y = random.uniform(camera_rect.top - SPAWN_MARGIN,
                                   camera_rect.bottom + SPAWN_MARGIN)

            # Clamp to arena
            x = max(30, min(ARENA_WIDTH - 30, x))
            y = max(30, min(ARENA_HEIGHT - 30, y))

            # Ensure minimum distance from player
            dx = x - player_x
            dy = y - player_y
            if math.sqrt(dx * dx + dy * dy) >= SPAWN_MIN_DIST:
                return x, y

        # Fallback: random position far from player
        angle = random.uniform(0, math.pi * 2)
        dist = SPAWN_MIN_DIST + 100
        x = player_x + math.cos(angle) * dist
        y = player_y + math.sin(angle) * dist
        x = max(30, min(ARENA_WIDTH - 30, x))
        y = max(30, min(ARENA_HEIGHT - 30, y))
        return x, y

    def update(self, dt, enemy_group, player_x, player_y, camera_rect):
        """Update wave logic. Returns True when a new wave starts."""
        self.enemies_alive = len(enemy_group)
        self.wave_announcement_timer = max(0, self.wave_announcement_timer - dt)

        if self.wave_active:
            # Check if wave is cleared
            if self.enemies_alive == 0:
                self.wave_active = False
                self.wave_timer = WAVE_BREAK_TIME
            return False
        else:
            # Waiting for next wave
            self.wave_timer -= dt
            if self.wave_timer <= 0:
                self.wave += 1
                self.wave_active = True
                self.wave_announcement_timer = 2.0
                self._spawn_wave(enemy_group, player_x, player_y, camera_rect)
                return True
        return False

    def _spawn_wave(self, enemy_group, player_x, player_y, camera_rect):
        """Spawn all enemies for the current wave."""
        wave_def = self._generate_wave(self.wave)

        for _ in range(wave_def.chasers):
            x, y = self._get_spawn_pos(player_x, player_y, camera_rect)
            enemy = Chaser(x, y, wave_def.hp_mult, wave_def.speed_mult,
                           wave_def.damage_mult)
            enemy_group.add(enemy)

        for _ in range(wave_def.shooters):
            x, y = self._get_spawn_pos(player_x, player_y, camera_rect)
            enemy = Shooter(x, y, wave_def.hp_mult, wave_def.speed_mult,
                            wave_def.damage_mult, wave_num=self.wave)
            enemy_group.add(enemy)

        for _ in range(wave_def.tanks):
            x, y = self._get_spawn_pos(player_x, player_y, camera_rect)
            enemy = Tank(x, y, wave_def.hp_mult, wave_def.speed_mult,
                         wave_def.damage_mult)
            enemy_group.add(enemy)

    def on_enemy_killed(self):
        """Called when an enemy is killed."""
        self.total_enemies_killed += 1

    @property
    def wave_info(self):
        return {
            "wave": self.wave,
            "enemies_alive": self.enemies_alive,
            "total_killed": self.total_enemies_killed,
            "announcing": self.wave_announcement_timer > 0,
        }

