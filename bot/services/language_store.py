from __future__ import annotations

import json
from pathlib import Path


class UserLanguageStore:
    def __init__(self, storage_path: Path) -> None:
        self.storage_path = storage_path
        self._state = self._load()

    def _load(self) -> dict[str, str]:
        if not self.storage_path.exists():
            return {}

        try:
            return json.loads(self.storage_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}

    def _save(self) -> None:
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.storage_path.write_text(
            json.dumps(self._state, ensure_ascii=True, indent=2, sort_keys=True),
            encoding="utf-8",
        )

    def get(self, user_id: int, default: str = "ru") -> str:
        return self._state.get(str(user_id), default)

    def set(self, user_id: int, language: str) -> None:
        self._state[str(user_id)] = language
        self._save()
