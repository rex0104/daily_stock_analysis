"""Per-user config storage in the users.settings JSON column."""

from __future__ import annotations

import json
import hashlib
import logging
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple

from dotenv import dotenv_values

logger = logging.getLogger(__name__)


class UserConfigManager:
    """Read/write user config from DB, with .env.example as defaults.

    Implements the same interface as ``ConfigManager``:
    - ``read_config_map()``
    - ``get_config_version()``
    - ``get_updated_at()``
    - ``apply_updates()``
    """

    def __init__(
        self,
        session_factory,
        user_id: str,
        env_example_path: Optional[Path] = None,
    ):
        self._sf = session_factory
        self._user_id = user_id
        self._env_example_path = env_example_path or (
            Path(__file__).resolve().parent.parent.parent / ".env.example"
        )

    # ------------------------------------------------------------------
    # Public interface (matches ConfigManager)
    # ------------------------------------------------------------------

    def read_config_map(self) -> Dict[str, str]:
        """Read merged config: user settings over .env.example defaults."""
        defaults = self._read_env_example()
        user_settings = self._read_user_settings()
        merged = {**defaults, **user_settings}
        return {k: v for k, v in merged.items() if v is not None}

    def get_config_version(self) -> str:
        """Version string for optimistic concurrency."""
        raw = json.dumps(self._read_user_settings(), sort_keys=True)
        h = hashlib.sha256(raw.encode()).hexdigest()[:16]
        return f"user:{h}"

    def get_updated_at(self) -> Optional[str]:
        """Return None — per-user settings don't track update timestamps yet."""
        return None

    def apply_updates(
        self,
        updates: Iterable[Tuple[str, str]],
        sensitive_keys: Set[str],
        mask_token: str,
    ) -> Tuple[List[str], List[str], str]:
        """Apply config updates to user's DB settings."""
        current = self._read_user_settings()
        updated_keys: List[str] = []
        skipped_masked: List[str] = []

        for key, value in updates:
            if key in sensitive_keys and value == mask_token:
                if key in current and current[key]:
                    skipped_masked.append(key)
                continue
            if current.get(key) == value:
                continue  # unchanged
            current[key] = value
            updated_keys.append(key)

        if updated_keys:
            self._write_user_settings(current)

        new_version = self.get_config_version()
        return updated_keys, skipped_masked, new_version

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _read_env_example(self) -> Dict[str, str]:
        if not self._env_example_path.exists():
            return {}
        raw = dotenv_values(self._env_example_path)
        return {k: v for k, v in raw.items() if v is not None}

    def _read_user_settings(self) -> Dict[str, str]:
        from src.storage import User

        with self._sf() as session:
            user = session.query(User).filter_by(id=self._user_id).first()
            if not user or not user.settings:
                return {}
            try:
                return json.loads(user.settings)
            except (json.JSONDecodeError, TypeError):
                return {}

    def _write_user_settings(self, settings: Dict[str, str]) -> None:
        from src.storage import User

        with self._sf() as session:
            user = session.query(User).filter_by(id=self._user_id).first()
            if user:
                user.settings = json.dumps(settings, ensure_ascii=False)
                session.commit()
