from __future__ import annotations

import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Dict


@dataclass
class StoredFile:
    file_id: str
    filename: str
    path: Path


class SessionStore:
    def __init__(self, base_dir: Path) -> None:
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._files: Dict[str, StoredFile] = {}

    def save_upload(self, filename: str, content: bytes, suffix: str) -> StoredFile:
        file_id = str(uuid.uuid4())
        path = self.base_dir / f"{file_id}{suffix}"
        path.write_bytes(content)
        stored = StoredFile(file_id=file_id, filename=filename, path=path)
        self._files[file_id] = stored
        return stored

    def get(self, file_id: str) -> StoredFile:
        if file_id not in self._files:
            raise KeyError(f"file_id not found: {file_id}")
        return self._files[file_id]
