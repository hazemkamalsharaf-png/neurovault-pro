"""
settings.py — Persistent application settings for NeuroVault Pro.

Settings are stored in a JSON file and loaded on startup.  All values have
sensible defaults so the app works out of the box even with no config file.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Default values
# ---------------------------------------------------------------------------

DEFAULTS = {
    "llm_endpoint": "http://127.0.0.1:1234/v1",
    "temperature": 0.3,
    "max_tokens": 1024,
    "request_timeout": 180,
    "chat_history_limit": 50,
}


# ---------------------------------------------------------------------------
# Settings dataclass
# ---------------------------------------------------------------------------

@dataclass
class AppSettings:
    """Application settings with JSON persistence."""

    # LLM / AI
    llm_endpoint: str = DEFAULTS["llm_endpoint"]
    temperature: float = DEFAULTS["temperature"]
    max_tokens: int = DEFAULTS["max_tokens"]
    request_timeout: int = DEFAULTS["request_timeout"]

    # Chat
    chat_history_limit: int = DEFAULTS["chat_history_limit"]

    # -- persistence --------------------------------------------------------

    def __post_init__(self) -> None:
        # Clamp values to sensible ranges
        self.temperature = max(0.0, min(2.0, self.temperature))
        self.max_tokens = max(64, min(8192, self.max_tokens))
        self.request_timeout = max(5, min(600, self.request_timeout))
        self.chat_history_limit = max(1, min(500, self.chat_history_limit))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AppSettings":
        # Only accept known keys (ignore extra/unknown fields gracefully)
        valid_keys = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered)

    @classmethod
    def load(cls, path: str | Path = "data/settings.json") -> "AppSettings":
        """Load settings from JSON file, falling back to defaults."""
        p = Path(path)
        if not p.exists():
            logger.info("No settings file found — using defaults.")
            return cls()
        try:
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
            settings = cls.from_dict(data)
            logger.info("Settings loaded from %s", p)
            return settings
        except (json.JSONDecodeError, KeyError) as exc:
            logger.warning("Failed to load settings (%s) — using defaults.", exc)
            return cls()

    def save(self, path: str | Path = "data/settings.json") -> None:
        """Persist settings to JSON file."""
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)
        logger.info("Settings saved to %s", p)


# ---------------------------------------------------------------------------
# SettingsManager — bridges settings changes to running components
# ---------------------------------------------------------------------------

class SettingsManager:
    """Manages settings and notifies listeners when values change."""

    def __init__(self, settings_path: str | Path = "data/settings.json"):
        self._settings = AppSettings.load(settings_path)
        self._listeners: list[Callable[[AppSettings], None]] = []

    @property
    def settings(self) -> AppSettings:
        return self._settings

    def get_endpoint(self) -> str:
        return self._settings.llm_endpoint

    def get_temperature(self) -> float:
        return self._settings.temperature

    def get_max_tokens(self) -> int:
        return self._settings.max_tokens

    def get_request_timeout(self) -> int:
        return self._settings.request_timeout

    def get_chat_history_limit(self) -> int:
        return self._settings.chat_history_limit

    # -- mutation -----------------------------------------------------------

    def set_llm_endpoint(self, value: str) -> None:
        self._settings.llm_endpoint = value
        self._notify()

    def set_temperature(self, value: float) -> None:
        self._settings.temperature = float(value)
        self._notify()

    def set_max_tokens(self, value: int) -> None:
        self._settings.max_tokens = int(value)
        self._notify()

    def set_request_timeout(self, value: int) -> None:
        self._settings.request_timeout = int(value)
        self._notify()

    def set_chat_history_limit(self, value: int) -> None:
        self._settings.chat_history_limit = int(value)
        self._notify()

    def save(self) -> None:
        """Write current settings to disk."""
        self._settings.save()

    # -- listeners ----------------------------------------------------------

    def on_change(self, callback: Callable[[AppSettings], None]) -> None:
        """Register a listener that fires after every settings change."""
        self._listeners.append(callback)

    def _notify(self) -> None:
        for cb in self._listeners:
            try:
                cb(self._settings)
            except Exception as exc:
                logger.error("Settings listener error: %s", exc)
