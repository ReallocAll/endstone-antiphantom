"""UUID preferences with validate-then-load and replace-then-publish semantics."""

import json
import os
from pathlib import Path
import tempfile
from uuid import UUID


def _unique_object(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


class Preferences:
    def __init__(self, path: Path):
        self.path = path
        self._players: dict[str, bool] = {}
        # FileNotFoundError is the only condition that means a new installation.
        try:
            text = path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return
        data = json.loads(text, object_pairs_hook=_unique_object)
        if not isinstance(data, dict) or set(data) != {"version", "players"}:
            raise ValueError("Preferences must contain exactly version and players")
        if type(data["version"]) is not int or data["version"] != 1:
            raise ValueError("Unsupported preferences version")
        if not isinstance(data["players"], dict):
            raise ValueError("Preferences players must be an object")
        validated = {}
        for key, enabled in data["players"].items():
            if str(UUID(key)) != key or type(enabled) is not bool:
                raise ValueError("Each preference must map a canonical UUID to a boolean")
            validated[key] = enabled
        self._players = validated

    def enabled(self, unique_id: UUID) -> bool:
        return self._players.get(str(unique_id), True)

    def set_enabled(self, unique_id: UUID, enabled: bool) -> None:
        if not isinstance(unique_id, UUID) or type(enabled) is not bool:
            raise ValueError("A UUID and boolean are required")
        updated = dict(self._players)
        updated[str(unique_id)] = enabled
        payload = json.dumps({"version": 1, "players": updated}, indent=2, sort_keys=True) + "\n"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=self.path.parent,
                prefix=f".{self.path.name}.", suffix=".tmp", delete=False,
            ) as file:
                temporary = Path(file.name)
                file.write(payload)
                file.flush()
                os.fsync(file.fileno())
            os.replace(temporary, self.path)
            temporary = None
        finally:
            if temporary is not None:
                try:
                    temporary.unlink(missing_ok=True)
                except OSError:
                    pass  # Preserve the original save error; never load leftover temporary files.
        # The old in-memory preference survives every pre-replacement failure.
        self._players = updated
