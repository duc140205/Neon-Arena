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
ARENA_WIDTH = 2400
ARENA_HEIGHT = 2400
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

# ── Enemy Settings ───────────────────────────────────────
# Chaser
CHASER_SPEED = 150
CHASER_HP = 50
CHASER_SIZE = 16
CHASER_DAMAGE = 15
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
TANK_DAMAGE = 30
TANK_XP = 50
TANK_COLOR = NEON_PURPLE

# ── Wave Settings ────────────────────────────────────────
WAVE_BREAK_TIME = 3.0       # seconds between waves
SPAWN_MARGIN = 100          # min distance from screen edge for spawning
SPAWN_MIN_DIST = 300        # min distance from player

# ── XP / Leveling ───────────────────────────────────────
BASE_XP_REQUIRED = 100
XP_SCALE_FACTOR = 1.4       # XP required multiplier per level

# ── Difficulty Scaling ──────────────────────────────────
# Applied per player level-up on top of wave scaling
DIFFICULTY_HP_PER_LEVEL = 0.05      # +5% enemy HP per player level
DIFFICULTY_SPEED_PER_LEVEL = 0.02   # +2% enemy speed per player level
DIFFICULTY_DAMAGE_PER_LEVEL = 0.03  # +3% enemy damage per player level

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
        "max_level": 2,
    },
}

# ── Particles ────────────────────────────────────────────
PARTICLE_GRAVITY = 0
MAX_PARTICLES = 500
