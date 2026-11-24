"""Small transparent JSON cache for external data providers."""

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any


class JsonResponseCache:
    """Persist raw provider responses with fetch timestamps and source labels."""

    def __init__(self, directory: str | Path, ttl_hours: float = 24.0) -> None:
        self.directory = Path(directory)
        self.ttl = timedelta(hours=ttl_hours)

    def _path(self, provider: str, key: str) -> Path:
        safe_key = "".join(
            character if character.isalnum() else "_" for character in key
        )
        return self.directory / provider / f"{safe_key}.json"

    def get(self, provider: str, key: str) -> dict[str, Any] | None:
        """Return a fresh cached payload, or None when absent or expired."""
        path = self._path(provider, key)
        if not path.is_file():
            return None
        try:
            record = json.loads(path.read_text())
            fetched_at = datetime.fromisoformat(record["fetched_at"])
        except (json.JSONDecodeError, KeyError, ValueError):
            return None
        if datetime.now(UTC) - fetched_at > self.ttl:
            return None
        payload = record.get("payload")
        return payload if isinstance(payload, dict) else None

    def set(
        self,
        provider: str,
        key: str,
        payload: dict[str, Any],
        *,
        source: str,
    ) -> Path:
        """Persist a provider response without credentials in its metadata."""
        path = self._path(provider, key)
        path.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "provider": provider,
            "key": key,
            "source": source,
            "fetched_at": datetime.now(UTC).isoformat(),
            "payload": payload,
        }
        path.write_text(json.dumps(record, indent=2, sort_keys=True))
        return path
