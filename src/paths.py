"""
Centralized path resolver for WhisperWriter.

Handles the difference between running from source (dev mode) and
running from a PyInstaller-frozen executable.

In frozen mode:
  - Read-only assets (icons, sounds, schema) are bundled inside _MEIPASS
  - Writable files (config.yaml, .env) live next to the exe
In dev mode:
  - Everything is relative to the project root (parent of src/)
"""

import os
import sys


def is_frozen() -> bool:
    """Return True if running from a PyInstaller bundle."""
    return getattr(sys, 'frozen', False)


def get_base_dir() -> str:
    """Return the project root (dev) or the exe directory (frozen)."""
    if is_frozen():
        # sys.executable is the .exe path; its parent is the one-folder dir
        return os.path.dirname(sys.executable)
    else:
        # In dev mode, src/ files are inside <project_root>/src/
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_bundle_dir() -> str:
    """Return the directory where bundled read-only data lives.

    In frozen mode this is sys._MEIPASS (temp extraction folder).
    In dev mode this is the project root.
    """
    if is_frozen():
        return sys._MEIPASS
    else:
        return get_base_dir()


def get_asset_path(*parts: str) -> str:
    """Return the absolute path to a bundled asset file.

    Example: get_asset_path('ww-logo.png') -> '<bundle>/assets/ww-logo.png'
    """
    return os.path.join(get_bundle_dir(), 'assets', *parts)


def get_schema_path() -> str:
    """Return the absolute path to config_schema.yaml (read-only, bundled)."""
    return os.path.join(get_bundle_dir(), 'src', 'config_schema.yaml')


def get_config_path() -> str:
    """Return the absolute path to config.yaml (writable).

    In frozen mode: next to the exe.
    In dev mode: <project_root>/src/config.yaml
    """
    if is_frozen():
        return os.path.join(get_base_dir(), 'config.yaml')
    else:
        return os.path.join(get_base_dir(), 'src', 'config.yaml')


def get_env_path() -> str:
    """Return the absolute path to .env file (writable)."""
    return os.path.join(get_base_dir(), '.env')


def get_history_path() -> str:
    """Return the absolute path to history.json (writable).

    In frozen mode: next to the exe.
    In dev mode: <project_root>/src/history.json
    """
    if is_frozen():
        return os.path.join(get_base_dir(), 'history.json')
    else:
        return os.path.join(get_base_dir(), 'src', 'history.json')
