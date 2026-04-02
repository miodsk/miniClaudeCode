from __future__ import annotations

# pyright: reportAny=false, reportUnknownArgumentType=false, reportUnknownMemberType=false, reportUnknownVariableType=false

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile


SerializedMessage = dict[str, object]
SessionPayload = dict[str, object]


@dataclass(slots=True)
class SessionData:
    session_id: str = "sess_default"
    messages: list[SerializedMessage] = field(default_factory=list)
    metadata: dict[str, object] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, payload: object) -> SessionData:
        if payload is None:
            return cls()
        if not isinstance(payload, dict):
            raise ValueError("Session payload must be a dict")

        session_id = payload.get("session_id", "sess_default")
        messages = payload.get("messages", [])
        metadata = payload.get("metadata", {})

        if not isinstance(session_id, str):
            raise ValueError("session_id must be a string")
        if not isinstance(messages, list):
            raise ValueError("messages must be a list")
        if not all(isinstance(message, dict) for message in messages):
            raise ValueError("messages must contain dict entries")
        if not isinstance(metadata, dict):
            raise ValueError("metadata must be a dict")

        return cls(
            session_id=session_id,
            messages=[dict(message) for message in messages],
            metadata=dict(metadata),
        )

    def to_dict(self) -> SessionPayload:
        return {
            "session_id": self.session_id,
            "messages": self.messages,
            "metadata": self.metadata,
        }


class SessionStore:
    session_file: Path = Path(".sessions/default.json")

    def __init__(self, session_file: Path | None = None):
        self.session_file = session_file or type(self).session_file

    def load(self) -> SessionPayload:
        if not self.session_file.exists():
            return SessionData().to_dict()

        try:
            payload: object = json.loads(self.session_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            self._backup_corrupt_file()
            return SessionData().to_dict()

        try:
            return SessionData.from_dict(payload).to_dict()
        except TypeError, ValueError:
            return SessionData().to_dict()

    def save(self, session: SessionPayload) -> None:
        session_data = SessionData.from_dict(session)
        self.session_file.parent.mkdir(parents=True, exist_ok=True)

        temp_path: Path | None = None
        try:
            with NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=self.session_file.parent,
                prefix=f"{self.session_file.stem}.",
                suffix=".tmp",
                delete=False,
            ) as temp_file:
                json.dump(
                    session_data.to_dict(),
                    temp_file,
                    indent=4,
                    ensure_ascii=False,
                )
                temp_file.flush()
                os.fsync(temp_file.fileno())
                temp_path = Path(temp_file.name)

            os.replace(temp_path, self.session_file)
        except Exception:
            if temp_path is not None and temp_path.exists():
                temp_path.unlink(missing_ok=True)
            raise

    def reset(self) -> None:
        self.session_file.unlink(missing_ok=True)

    def _backup_corrupt_file(self) -> None:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        backup_path = self.session_file.with_name(
            f"{self.session_file.name}.bak-{timestamp}"
        )
        os.replace(self.session_file, backup_path)


__all__ = ["SessionData", "SessionStore"]
