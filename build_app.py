"""
build_app.py - PyInstaller Build Script for Neon Arena
======================================================
Automates the packaging of the Neon Arena Pygame project into a single
Windows .exe file.

Usage:
    python build_app.py

Requirements:
    pip install pyinstaller pygame

What it does:
    1. Bundles main.py + the arena_shooter package into one .exe
    2. Includes settings.json as a bundled data file (default config)
    3. Sets --noconsole so no terminal window appears
    4. Enables DPI awareness via the app manifest
    5. Outputs: dist/NeonArena.exe
"""

import subprocess
import sys
import os
import shutil
import glob

# ── Configuration ────────────────────────────────────────────────────────────
APP_NAME = "NeonArena"
ENTRY_POINT = "main.py"
ICON_PATH = os.path.join("assets", "icons", "neonarena.ico")

# Project root = directory this script lives in
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# Data files to bundle: (source_path, destination_inside_bundle)
# settings.json is placed at the bundle root so resource_path("settings.json") works.
_ALL_DATA_FILES = [
    (os.path.join(PROJECT_ROOT, "settings.json"), "."),
]

# Auto-discover every file inside the assets/ tree and preserve the
# relative directory structure inside the bundle.
ASSETS_ROOT = os.path.join(PROJECT_ROOT, "assets")
for _abs_path in glob.glob(os.path.join(ASSETS_ROOT, "**", "*"), recursive=True):
    if os.path.isfile(_abs_path):
        # e.g. assets/sounds/sfx/hover.wav  →  dest = assets/sounds/sfx
        _rel_dir = os.path.relpath(os.path.dirname(_abs_path), PROJECT_ROOT)
        _ALL_DATA_FILES.append((_abs_path, _rel_dir))

# Only include files that actually exist
DATA_FILES = []
for _src, _dest in _ALL_DATA_FILES:
    if os.path.exists(_src):
        DATA_FILES.append((_src, _dest))
    else:
        print(f"  ⚠ Data file not found (skipping): {_src}")

# Hidden imports PyInstaller might miss (relative imports inside packages)
HIDDEN_IMPORTS = [
    "arena_shooter",
    "arena_shooter.game",
    "arena_shooter.config",
    "arena_shooter.settings",
    "arena_shooter.player",
    "arena_shooter.camera",
    "arena_shooter.enemies",
    "arena_shooter.enemy_manager",
    "arena_shooter.particles",
    "arena_shooter.projectiles",
    "arena_shooter.ui",
    "arena_shooter.settings_menu",
    "arena_shooter.obstacles",
]


def clean_build_artifacts():
    """Delete stale build/, dist/, and all __pycache__/ trees so PyInstaller
    always compiles from the latest source files."""
    print("  Cleaning previous build artifacts...")

    for folder in ("build", "dist"):
        target = os.path.join(PROJECT_ROOT, folder)
        if os.path.isdir(target):
            shutil.rmtree(target)
            print(f"    Removed: {target}")

    # Remove every __pycache__ directory under the project root
    for cache_dir in glob.glob(
        os.path.join(PROJECT_ROOT, "**", "__pycache__"), recursive=True
    ):
        if os.path.isdir(cache_dir):
            shutil.rmtree(cache_dir)
            print(f"    Removed: {cache_dir}")

    print("  Done.")
    print()


def build():
    """Clean stale artifacts, then construct and execute the PyInstaller command."""
    clean_build_artifacts()

    cmd = [
        sys.executable, "-m", "PyInstaller",

        # ── Output mode ──────────────────────────────────
        "--onefile",          # Single .exe output
        "--noconsole",        # No terminal window (windowed app)

        # ── App identity ─────────────────────────────────
        "--name", APP_NAME,

        # ── Data files ───────────────────────────────────
    ]

    # Add each data file with --add-data src;dest (Windows uses ;)
    for src, dest in DATA_FILES:
        cmd.extend(["--add-data", f"{src};{dest}"])

    # Add hidden imports
    for imp in HIDDEN_IMPORTS:
        cmd.extend(["--hidden-import", imp])

    # ── DPI Awareness manifest ───────────────────────────
    # This tells Windows the app is DPI-aware, preventing automatic
    # scaling that causes blurriness. Works alongside the ctypes
    # SetProcessDpiAwareness() call in main.py.
    manifest = os.path.join(PROJECT_ROOT, "NeonArena.manifest")
    if os.path.exists(manifest):
        cmd.extend(["--manifest", manifest])

    # ── Icon (optional) ──────────────────────────────────
    if ICON_PATH and os.path.exists(os.path.join(PROJECT_ROOT, ICON_PATH)):
        cmd.extend(["--icon", os.path.join(PROJECT_ROOT, ICON_PATH)])

    # ── Overwrite previous build without asking ──────────
    cmd.append("--noconfirm")

    # ── Clean build artifacts ────────────────────────────
    cmd.append("--clean")

    # ── Entry point ──────────────────────────────────────
    cmd.append(os.path.join(PROJECT_ROOT, ENTRY_POINT))

    # Print the full command for debugging
    print("=" * 70)
    print("  NEON ARENA — PyInstaller Build")
    print("=" * 70)
    print()
    print("Command:")
    print("  " + " ".join(cmd))
    print()

    # Execute
    result = subprocess.run(cmd, cwd=PROJECT_ROOT)

    if result.returncode == 0:
        exe_path = os.path.join(PROJECT_ROOT, "dist", f"{APP_NAME}.exe")
        print()
        print("=" * 70)
        print(f"  ✅ BUILD SUCCESSFUL!")
        print(f"  Output: {exe_path}")
        print()
        print("  NOTE: When distributing, you may want to include a copy of")
        print("  settings.json next to the .exe so users can customize their")
        print("  display settings. If missing, the app uses built-in defaults.")
        print("=" * 70)
    else:
        print()
        print("=" * 70)
        print("  ❌ BUILD FAILED — check the output above for errors.")
        print("=" * 70)
        sys.exit(1)


if __name__ == "__main__":
    build()
