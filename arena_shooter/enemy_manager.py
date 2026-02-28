"""
enemy_manager.py - Wave spawning and difficulty scaling
"""

import random
import math
from .enemies import Chaser, Shooter, Tank, Boss, SniperBoss, SlimeBoss, SuicideBomber, ShieldGuard
from .settings import (
    ARENA_WIDTH, ARENA_HEIGHT, SPAWN_MARGIN, SPAWN_MIN_DIST,
    WAVE_BREAK_TIME, SCREEN_WIDTH, SCREEN_HEIGHT,
    DIFFICULTY_HP_PER_LEVEL, DIFFICULTY_SPEED_PER_LEVEL,
    DIFFICULTY_DAMAGE_PER_LEVEL,
    BOSS_WAVE_INTERVAL, BOSS_SLAM_DAMAGE, BOSS_DIFFICULTY_BOOST,
    SLIME_BOSS_SHOCKWAVE_DAMAGE,
    BOMBER_SPAWN_WAVE, SHIELD_GUARD_SPAWN_WAVE,
    SPAWN_STAGGER_DELAY,
)


class WaveDefinition:
    """Defines a single wave's enemy composition."""

    def __init__(self, chasers=0, shooters=0, tanks=0, bombers=0, guards=0,
                 hp_mult=1.0, speed_mult=1.0, damage_mult=1.0):
        self.chasers = chasers
        self.shooters = shooters
        self.tanks = tanks
        self.bombers = bombers
        self.guards = guards
        self.hp_mult = hp_mult
        self.speed_mult = speed_mult
        self.damage_mult = damage_mult

    @property
    def total(self):
        return self.chasers + self.shooters + self.tanks + self.bombers + self.guards


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
        self.boss_difficulty_bonus = 0.0  # permanent bonus from boss kills

        # Boss tracking
        self.active_boss = None
        self.boss_wave = False

        # Staggered spawn queue: list of (EnemyClass, hp_mult, speed_mult, damage_mult, extra_kwargs)
        self._pending_spawns = []
        self._spawn_stagger_timer = 0.0

    def set_difficulty(self, player_level):
        """Update difficulty based on player level."""
        lvl = player_level - 1
        self.difficulty_factor = 1.0 + lvl * 0.05 + self.boss_difficulty_bonus

    def _is_boss_wave(self, wave_num):
        """Check if this wave is a boss fight."""
        return wave_num > 0 and wave_num % BOSS_WAVE_INTERVAL == 0

    def _generate_wave(self, wave_num):
        """Generate a wave definition based on wave number."""
        chasers = 3 + wave_num * 2
        shooters = max(0, wave_num - 1)
        tanks = max(0, (wave_num - 3) // 2)

        chasers = min(chasers, 20)
        shooters = min(shooters, 10)
        tanks = min(tanks, 5)

        # SuicideBombers from wave 5
        bombers = max(0, (wave_num - BOMBER_SPAWN_WAVE + 1)) if wave_num >= BOMBER_SPAWN_WAVE else 0
        bombers = min(bombers, 6)

        # ShieldGuards from wave 8
        guards = max(0, (wave_num - SHIELD_GUARD_SPAWN_WAVE + 2) // 2) if wave_num >= SHIELD_GUARD_SPAWN_WAVE else 0
        guards = min(guards, 4)

        wave_hp = 1.0 + (wave_num - 1) * 0.1
        wave_speed = 1.0 + (wave_num - 1) * 0.03
        wave_damage = 1.0 + (wave_num - 1) * 0.05

        df = self.difficulty_factor
        hp_mult = wave_hp * (1.0 + (df - 1.0) * DIFFICULTY_HP_PER_LEVEL / 0.05)
        speed_mult = wave_speed * (1.0 + (df - 1.0) * DIFFICULTY_SPEED_PER_LEVEL / 0.05)
        damage_mult = wave_damage * (1.0 + (df - 1.0) * DIFFICULTY_DAMAGE_PER_LEVEL / 0.05)

        return WaveDefinition(chasers, shooters, tanks, bombers, guards,
                              hp_mult, speed_mult, damage_mult)

    def _get_spawn_pos(self, player_x, player_y, camera_rect):
        """Get a valid spawn position outside the camera view but inside arena."""
        for _ in range(50):
            side = random.randint(0, 3)
            if side == 0:
                x = random.uniform(camera_rect.left - SPAWN_MARGIN,
                                   camera_rect.right + SPAWN_MARGIN)
                y = camera_rect.top - random.uniform(50, SPAWN_MARGIN)
            elif side == 1:
                x = random.uniform(camera_rect.left - SPAWN_MARGIN,
                                   camera_rect.right + SPAWN_MARGIN)
                y = camera_rect.bottom + random.uniform(50, SPAWN_MARGIN)
            elif side == 2:
                x = camera_rect.left - random.uniform(50, SPAWN_MARGIN)
                y = random.uniform(camera_rect.top - SPAWN_MARGIN,
                                   camera_rect.bottom + SPAWN_MARGIN)
            else:
                x = camera_rect.right + random.uniform(50, SPAWN_MARGIN)
                y = random.uniform(camera_rect.top - SPAWN_MARGIN,
                                   camera_rect.bottom + SPAWN_MARGIN)

            x = max(30, min(ARENA_WIDTH - 30, x))
            y = max(30, min(ARENA_HEIGHT - 30, y))

            dx = x - player_x
            dy = y - player_y
            if math.sqrt(dx * dx + dy * dy) >= SPAWN_MIN_DIST:
                return x, y

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

        # Track boss state
        if self.active_boss and not self.active_boss.alive():
            # Boss defeated — permanent difficulty boost
            self.boss_difficulty_bonus += BOSS_DIFFICULTY_BOOST
            self.difficulty_factor += BOSS_DIFFICULTY_BOOST
            self.active_boss = None

        # Spawn boss minions
        if self.active_boss and self.active_boss.alive():
            # Spawn boss minions (original Boss)
            if self.active_boss.pending_minions:
                for mx, my in self.active_boss.pending_minions:
                    mx = max(30, min(ARENA_WIDTH - 30, mx))
                    my = max(30, min(ARENA_HEIGHT - 30, my))
                    minion = Chaser(mx, my, 1.0, 1.0, 1.0)
                    enemy_group.add(minion)
                self.active_boss.pending_minions.clear()

            # Handle SlimeBoss toxic pools
            if hasattr(self.active_boss, 'toxic_pools') and self.active_boss.toxic_pools:
                # Transfer toxic pool data to game's ghost_trails system
                # (game.py will pick them up via active_boss.toxic_pools)
                pass  # toxic_pools stay on the boss; game.py reads them

        if self.wave_active:
            # Drain the staggered spawn queue
            if self._pending_spawns:
                self._spawn_stagger_timer -= dt
                if self._spawn_stagger_timer <= 0:
                    cls, hp_m, spd_m, dmg_m, kwargs = self._pending_spawns.pop(0)
                    x, y = self._get_spawn_pos(player_x, player_y, camera_rect)
                    enemy = cls(x, y, hp_m, spd_m, dmg_m, **kwargs)
                    enemy_group.add(enemy)
                    self._spawn_stagger_timer = SPAWN_STAGGER_DELAY

            if self.enemies_alive == 0 and not self._pending_spawns:
                self.wave_active = False
                self.boss_wave = False
                self.wave_timer = WAVE_BREAK_TIME
            return False
        else:
            self.wave_timer -= dt
            if self.wave_timer <= 0:
                self.wave += 1
                self.wave_active = True
                self.wave_announcement_timer = 2.0

                if self._is_boss_wave(self.wave):
                    self.boss_wave = True
                    self._spawn_boss(enemy_group, player_x, player_y, camera_rect)
                else:
                    self._spawn_wave(enemy_group, player_x, player_y, camera_rect)
                return True
        return False

    def _spawn_boss(self, enemy_group, player_x, player_y, camera_rect):
        """Spawn a random boss type + a few escort enemies."""
        x, y = self._get_spawn_pos(player_x, player_y, camera_rect)
        wave_def = self._generate_wave(self.wave)

        # Randomly pick one of the three boss types
        boss_class = random.choice([Boss, SniperBoss, SlimeBoss])
        boss = boss_class(x, y, wave_def.hp_mult, wave_def.speed_mult,
                          wave_def.damage_mult)
        enemy_group.add(boss)
        self.active_boss = boss

        # Small escort
        for _ in range(3):
            ex, ey = self._get_spawn_pos(player_x, player_y, camera_rect)
            enemy_group.add(Chaser(ex, ey, wave_def.hp_mult, wave_def.speed_mult,
                                   wave_def.damage_mult))

    def _spawn_wave(self, enemy_group, player_x, player_y, camera_rect):
        """Queue enemies for staggered spawning during the wave."""
        wave_def = self._generate_wave(self.wave)

        queue = []
        for _ in range(wave_def.chasers):
            queue.append((Chaser, wave_def.hp_mult, wave_def.speed_mult,
                          wave_def.damage_mult, {}))
        for _ in range(wave_def.shooters):
            queue.append((Shooter, wave_def.hp_mult, wave_def.speed_mult,
                          wave_def.damage_mult, {"wave_num": self.wave}))
        for _ in range(wave_def.tanks):
            queue.append((Tank, wave_def.hp_mult, wave_def.speed_mult,
                          wave_def.damage_mult, {}))
        for _ in range(wave_def.bombers):
            queue.append((SuicideBomber, wave_def.hp_mult, wave_def.speed_mult,
                          wave_def.damage_mult, {}))
        for _ in range(wave_def.guards):
            queue.append((ShieldGuard, wave_def.hp_mult, wave_def.speed_mult,
                          wave_def.damage_mult, {}))

        # Shuffle so enemy types are interleaved
        random.shuffle(queue)
        self._pending_spawns = queue
        self._spawn_stagger_timer = 0.0  # spawn one immediately

    def on_enemy_killed(self):
        """Called when an enemy is killed."""
        self.total_enemies_killed += 1

    @property
    def wave_info(self):
        boss = self.active_boss
        return {
            "wave": self.wave,
            "enemies_alive": self.enemies_alive,
            "total_killed": self.total_enemies_killed,
            "announcing": self.wave_announcement_timer > 0,
            "boss_active": boss is not None and boss.alive(),
            "boss_hp": boss.hp if boss and boss.alive() else 0,
            "boss_max_hp": boss.max_hp if boss and boss.alive() else 1,
            "boss_wave": self.boss_wave,
        }
