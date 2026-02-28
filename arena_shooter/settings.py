"""
settings.py - Game constants, colors, and configuration
Cyberpunk Arena Shooter
"""

import math

# ── Display ──────────────────────────────────────────────
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
FPS = 60
TITLE = "NEON ARENA // Cyberpunk Shooter"

# ── Arena ────────────────────────────────────────────────
ARENA_WIDTH = 4000
ARENA_HEIGHT = 4000
GRID_SIZE = 80  # background grid cell size

# ── Cyberpunk Color Palette ──────────────────────────────
BLACK       = (5, 5, 15)
DARK_BG     = (10, 10, 25)
GRID_COLOR  = (20, 20, 50)

NEON_CYAN   = (0, 255, 255)
NEON_MAGENTA = (255, 0, 200)
NEON_PINK   = (255, 50, 120)
NEON_YELLOW = (255, 255, 50)
NEON_GREEN  = (50, 255, 100)
NEON_ORANGE = (255, 150, 30)
NEON_PURPLE = (180, 50, 255)
NEON_RED    = (255, 40, 40)
NEON_BLUE   = (50, 100, 255)

WHITE       = (255, 255, 255)
GRAY        = (100, 100, 120)
DARK_GRAY   = (40, 40, 60)

# Glow variations (semi-transparent)
GLOW_CYAN   = (0, 255, 255, 60)
GLOW_MAGENTA = (255, 0, 200, 60)
GLOW_PINK   = (255, 50, 120, 40)

# UI Colors
UI_BG       = (15, 15, 35, 200)
UI_BORDER   = (0, 200, 255, 180)
HP_BAR      = (255, 40, 80)
HP_BAR_BG   = (60, 20, 30)
XP_BAR      = (0, 220, 255)
XP_BAR_BG   = (20, 40, 60)
NEON_WHITE  = (220, 230, 255)

# ── Obstacles ────────────────────────────────────────────
OBSTACLE_COUNT = 25               # number of obstacles in the arena
OBSTACLE_MIN_SIZE = 40            # min width/height
OBSTACLE_MAX_SIZE = 120           # max width/height
OBSTACLE_COLOR = (30, 40, 80)     # dark neon fill
OBSTACLE_BORDER_COLOR = NEON_BLUE # neon border
OBSTACLE_SAFE_RADIUS = 300        # no obstacles near arena center (spawn)

# ── Power-Ups ────────────────────────────────────────────
POWERUP_SPAWN_INTERVAL = 12.0     # seconds between spawns
POWERUP_MAX_ACTIVE = 3            # max powerups in arena at once
POWERUP_RADIUS = 14               # pickup radius
POWERUP_LIFETIME = 15.0           # seconds before despawn
POWERUP_TYPES = {
    "health": {"name": "REPAIR", "color": NEON_GREEN, "icon": "+", "weight": 40},
    "shield": {"name": "SHIELD", "color": NEON_CYAN, "icon": "O", "weight": 30},
    "double_damage": {"name": "2x DMG", "color": NEON_YELLOW, "icon": "!", "weight": 20},
    "speed_boost": {"name": "SPEED", "color": NEON_MAGENTA, "icon": ">", "weight": 10},
}
SHIELD_DURATION = 5.0             # seconds
DOUBLE_DAMAGE_DURATION = 6.0      # seconds
SPEED_BOOST_DURATION = 5.0        # seconds
SPEED_BOOST_MULT = 1.5

# ── Player Settings ─────────────────────────────────────
PLAYER_SPEED = 300          # pixels per second
PLAYER_SIZE = 20            # radius
PLAYER_MAX_HP = 100
PLAYER_FIRE_RATE = 0.15     # seconds between shots
PLAYER_BULLET_SPEED = 700
PLAYER_BULLET_DAMAGE = 25
PLAYER_BULLET_SIZE = 5

# Dash
DASH_SPEED = 900
DASH_DURATION = 0.15        # seconds
DASH_COOLDOWN = 1.0         # seconds
DASH_PARTICLES = 15
DASH_DECAY_DURATION = 0.25  # seconds of lingering momentum after dash ends

# Dash upgrade constants
GHOST_TRAIL_DAMAGE = 15           # damage per tick from ghost trail
GHOST_TRAIL_INTERVAL = 0.03       # seconds between trail spawns
GHOST_TRAIL_LIFETIME = 0.8        # seconds trail lingers
GHOST_TRAIL_RADIUS = 18           # radius of each fire zone
SHOCKWAVE_RADIUS = 150            # radius of end-of-dash blast
SHOCKWAVE_PUSHBACK = 400          # push speed on enemies
REFLEX_FIRE_RATE_MULT = 0.5       # 50% faster fire rate
REFLEX_DURATION = 3.0             # seconds of boosted fire rate

# Shotgun (multi_barrel cone spread)
SHOTGUN_CONE_ANGLE = 0.6          # total cone half-angle in radians (~35°)

# Knockback (applied to enemies hit by PlayerBullet)
BULLET_KNOCKBACK_FACTOR = 0.35    # fraction of bullet speed applied as pushback

# Railgun power-up
RAILGUN_DURATION = 6.0            # seconds the railgun buff lasts
RAILGUN_BULLET_SPEED = 1200       # faster than normal bullets
RAILGUN_DAMAGE_MULT = 1.5         # damage multiplier over current bullet_damage
RAILGUN_SIZE = 8                  # slightly larger bullet

# Score & Combo system
COMBO_WINDOW = 2.0                # seconds before combo resets to 0
SCORE_MULTIPLIER = 1.0            # global score scaling factor
COMBO_TIER1_THRESHOLD = 5         # x5 combo milestone
COMBO_TIER2_THRESHOLD = 10        # x10 combo milestone

# ── Enemy Settings ───────────────────────────────────────
# Chaser
CHASER_SPEED = 150
CHASER_HP = 50
CHASER_SIZE = 16
CHASER_DAMAGE = 8
CHASER_XP = 20
CHASER_COLOR = NEON_RED

# Shooter
SHOOTER_SPEED = 80
SHOOTER_HP = 40
SHOOTER_SIZE = 18
SHOOTER_DAMAGE = 10
SHOOTER_FIRE_RATE = 1.5     # seconds
SHOOTER_BULLET_SPEED = 350
SHOOTER_PREFERRED_DIST = 250
SHOOTER_XP = 30
SHOOTER_COLOR = NEON_ORANGE

# Tank (slow, lots of HP)
TANK_SPEED = 60
TANK_HP = 200
TANK_SIZE = 28
TANK_DAMAGE = 18
TANK_XP = 50
TANK_COLOR = NEON_PURPLE

# ── Wave Settings ────────────────────────────────────────
WAVE_BREAK_TIME = 3.0       # seconds between waves
SPAWN_MARGIN = 100          # min distance from screen edge for spawning
SPAWN_MIN_DIST = 500        # min distance from player (was 300)
SPAWN_STAGGER_DELAY = 0.5   # seconds between each enemy spawn in a wave

# ── XP / Leveling ───────────────────────────────────────
BASE_XP_REQUIRED = 100
XP_SCALE_FACTOR = 1.4       # XP required multiplier per level

# ── Difficulty Scaling ──────────────────────────────────
# Applied per player level-up on top of wave scaling
DIFFICULTY_HP_PER_LEVEL = 0.05      # +5% enemy HP per player level
DIFFICULTY_SPEED_PER_LEVEL = 0.02   # +2% enemy speed per player level
DIFFICULTY_DAMAGE_PER_LEVEL = 0.03  # +3% enemy damage per player level

# ── Boss Settings ───────────────────────────────────────
BOSS_WAVE_INTERVAL = 5              # boss appears every N waves
BOSS_SPEED = 100
BOSS_HP = 2000
BOSS_SIZE = 40                      # radius
BOSS_DAMAGE = 25
BOSS_XP = 200
BOSS_COLOR = NEON_RED
BOSS_CHARGE_SPEED_MULT = 5.0       # speed multiplier during charge
BOSS_CHARGE_DURATION = 1.0          # seconds
BOSS_CHARGE_COOLDOWN = 4.0          # seconds between charges
BOSS_SLAM_RADIUS = 200              # AOE slam radius
BOSS_SLAM_DAMAGE = 50
BOSS_SLAM_COOLDOWN = 6.0            # seconds between slams
BOSS_MINION_COUNT = 3               # chasers spawned per summon
BOSS_MINION_COOLDOWN = 6.0          # seconds between minion spawns
BOSS_DIFFICULTY_BOOST = 0.15        # +15% permanent difficulty after boss kill

# ── SniperBoss Settings ─────────────────────────────────
SNIPER_BOSS_SPEED = 70
SNIPER_BOSS_HP = 1800
SNIPER_BOSS_SIZE = 36
SNIPER_BOSS_DAMAGE = 20
SNIPER_BOSS_XP = 250
SNIPER_BOSS_COLOR = NEON_CYAN
SNIPER_BOSS_PREFERRED_DIST = 600    # stays far from player
SNIPER_BOSS_FIRE_RATE = 2.0         # laser shot every 2 seconds
SNIPER_BOSS_BULLET_SPEED = 800      # high-speed laser
SNIPER_BOSS_RING_COOLDOWN = 5.0     # ring of death every 5 seconds
SNIPER_BOSS_RING_BULLET_COUNT = 12  # 12 bullets in 360 degrees
SNIPER_BOSS_RING_BULLET_SPEED = 400

# ── SlimeBoss Settings ──────────────────────────────────
SLIME_BOSS_SPEED = 50
SLIME_BOSS_HP = 2500
SLIME_BOSS_SIZE = 45
SLIME_BOSS_DAMAGE = 15
SLIME_BOSS_XP = 300
SLIME_BOSS_COLOR = NEON_GREEN
SLIME_BOSS_TRAIL_DAMAGE = 5         # damage per tick from toxic trail
SLIME_BOSS_TRAIL_INTERVAL = 0.15    # seconds between trail drops
SLIME_BOSS_TRAIL_LIFETIME = 3.0     # how long the toxic pool lasts
SLIME_BOSS_TRAIL_RADIUS = 25        # radius of each toxic pool
SLIME_BOSS_JUMP_COOLDOWN = 6.0      # seconds between jumps
SLIME_BOSS_JUMP_SPEED = 1200        # speed during jump
SLIME_BOSS_JUMP_DURATION = 0.4      # seconds of jump
SLIME_BOSS_SHOCKWAVE_RADIUS = 180   # landing shockwave radius
SLIME_BOSS_SHOCKWAVE_DAMAGE = 35    # landing shockwave damage

# ── Enemy Special Skills ────────────────────────────────
# Chaser — Burst Speed
CHASER_BURST_CHANCE = 0.008         # chance per frame (~0.8% per tick)
CHASER_BURST_SPEED_MULT = 3.0      # speed multiplier during burst
CHASER_BURST_DURATION = 0.4        # seconds

# Shooter — Fan Shot
SHOOTER_FAN_WAVE_THRESHOLD = 4     # wave number to unlock fan shot
SHOOTER_FAN_BULLET_COUNT = 3       # bullets in fan
SHOOTER_FAN_SPREAD = 0.35          # radians total spread

# Tank — Shield Phase
TANK_SHIELD_COOLDOWN = 8.0         # seconds between shields
TANK_SHIELD_DURATION = 3.0         # seconds shield lasts
TANK_SHIELD_REDUCTION = 0.7        # damage reduced (70% reduction)

# SuicideBomber
BOMBER_SPEED = 220                 # fast approach
BOMBER_HP = 30                     # fragile
BOMBER_SIZE = 14                   # small
BOMBER_DAMAGE = 60                 # explosion damage to player
BOMBER_XP = 35
BOMBER_COLOR = NEON_YELLOW
BOMBER_PRIME_RANGE = 60            # distance to start priming
BOMBER_PRIME_DURATION = 1.0        # seconds of flashing before boom
BOMBER_EXPLOSION_RADIUS = 120      # AOE radius of the detonation
BOMBER_SPAWN_WAVE = 5              # first wave they can appear
BOMBER_TURN_RATE = 4.0             # radians per second turning speed

# ShieldGuard
SHIELD_GUARD_SPEED = 45            # very slow
SHIELD_GUARD_HP = 250              # tanky
SHIELD_GUARD_SIZE = 26             # large
SHIELD_GUARD_DAMAGE = 15           # melee contact damage
SHIELD_GUARD_XP = 55
SHIELD_GUARD_COLOR = NEON_CYAN
SHIELD_GUARD_ARC = math.radians(120)  # front shield arc (120 degrees)
SHIELD_GUARD_SPAWN_WAVE = 8       # first wave they can appear
SHIELD_GUARD_TURN_RATE = 2.5      # radians per second turning speed

# ── Upgrades ─────────────────────────────────────────────
UPGRADES = {
    "fire_rate": {
        "name": "RAPID FIRE",
        "desc": "Fire Rate +20%",
        "icon": ">>",
        "color": NEON_YELLOW,
        "max_level": 8,
    },
    "bullet_speed": {
        "name": "VELOCITY",
        "desc": "Bullet Speed +15%",
        "icon": "→→",
        "color": NEON_CYAN,
        "max_level": 6,
    },
    "max_hp": {
        "name": "ARMOR UP",
        "desc": "Max HP +25",
        "icon": "+♥",
        "color": NEON_PINK,
        "max_level": 10,
    },
    "damage": {
        "name": "OVERCHARGE",
        "desc": "Damage +20%",
        "icon": "⚡",
        "color": NEON_ORANGE,
        "max_level": 8,
    },
    "move_speed": {
        "name": "ADRENALINE",
        "desc": "Move Speed +10%",
        "icon": "⇑",
        "color": NEON_GREEN,
        "max_level": 6,
    },
    "dash_cooldown": {
        "name": "PHASE SHIFT",
        "desc": "Dash Cooldown -15%",
        "icon": "◇",
        "color": NEON_PURPLE,
        "max_level": 5,
    },
    "giant_growth": {
        "name": "GIANT GROWTH",
        "desc": "Size↑ HP+50 Dmg+30%",
        "icon": "✦",
        "color": NEON_RED,
        "max_level": 4,
    },
    "multi_barrel": {
        "name": "MULTI-BARREL",
        "desc": "Extra barrel +1",
        "icon": "⊕",
        "color": NEON_BLUE,
        "max_level": 12,
    },
    "ghost_dash": {
        "name": "GHOST DASH",
        "desc": "Leave fire trail",
        "icon": "🔥",
        "color": NEON_ORANGE,
        "max_level": 3,
    },
    "dash_shockwave": {
        "name": "SHOCKWAVE",
        "desc": "Blast at dash end",
        "icon": "◎",
        "color": NEON_MAGENTA,
        "max_level": 3,
    },
    "reflex_dash": {
        "name": "REFLEX DASH",
        "desc": "Dash thru bullet=fast",
        "icon": "⟡",
        "color": NEON_WHITE,
        "max_level": 3,
    },
}

# ── Ultimate Skill: Neon Pulse ───────────────────────────
ULT_COOLDOWN = 45.0               # seconds between ultimate uses
ULT_CHARGE_PER_KILL = 5.0         # charge gained per enemy kill (out of ULT_COOLDOWN)
ULT_PULSE_RADIUS = 350            # base radius of the radial blast
ULT_PULSE_DAMAGE = 60             # base damage to enemies in radius
ULT_PUSHBACK_FORCE = 600          # pushback speed applied to enemies
ULT_SLOW_DURATION = 3.0           # seconds enemies are slowed
ULT_SLOW_FACTOR = 0.4             # enemy speed multiplied by this while slowed
ULT_LASER_COUNT = 6               # auto-aiming lasers (sniper augment)
ULT_LASER_DAMAGE = 40             # damage per laser
ULT_LASER_SPEED = 1400            # laser projectile speed
ULT_TOXIC_POOL_COUNT = 8          # toxic pools left (slime augment)
ULT_TOXIC_POOL_DAMAGE = 8         # damage per tick from toxic pool
ULT_TOXIC_POOL_LIFETIME = 4.0     # seconds toxic pool lasts
ULT_TOXIC_POOL_RADIUS = 30        # radius of each toxic pool
ULT_TANK_INVINCIBILITY = 4.0      # seconds of invincibility (tank augment)
ULT_TANK_PUSHBACK_MULT = 2.5      # knockback multiplier (tank augment)

# Trial challenge requirements
TRIAL_KILL_TARGET = 10            # kills within time limit (timed path)
TRIAL_EASY_KILL_TARGET = 5        # kills without taking damage (untouched path)
TRIAL_TIME_LIMIT = 15.0           # seconds to complete the timed path
TRIAL_START_INVINCIBILITY = 1.0   # invincibility bubble at trial start

# Ult speed boost
ULT_SPEED_BOOST_MULT = 1.3        # 30% movement speed during ultimate
ULT_SPEED_BOOST_DURATION = 3.0    # seconds of speed boost after ult activation

# ── Particles ────────────────────────────────────────────
PARTICLE_GRAVITY = 0
MAX_PARTICLES = 500
