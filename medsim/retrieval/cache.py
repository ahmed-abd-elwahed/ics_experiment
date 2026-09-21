"""Optional on-disk response cache keyed by (source, query, params_hash)."""

from __future__ import annotations

import hashlib
import json
import os
import threading
from pathlib import Path
from typing import Any


class ResponseCache:
    def __init__(self, directory: str | Path) -> None:
        self.directory = Path(directory)

    @staticmethod
    def params_hash(params: dict[str, Any]) -> str:
        blob = json.dumps(params, sort_keys=True, default=str)
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]

    def _path(self, source: str, query: str, params: dict[str, Any]) -> Path:
        key = json.dumps([source, query, self.params_hash(params)], ensure_ascii=False)
        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
        return self.directory / source / f"{digest}.json"

    def get(self, source: str, query: str, params: dict[str, Any]) -> Any | None:
        path = self._path(source, query, params)
        try:
            return json.loads(path.read_text(encoding="utf-8"))["payload"]
        except (OSError, ValueError, KeyError):
            return None

    def set(self, source: str, query: str, params: dict[str, Any], payload: Any) -> None:
        path = self._path(source, query, params)
        path.parent.mkdir(parents=True, exist_ok=True)
        record = {"source": source, "query": query, "params": params, "payload": payload}
        # One temporary file per process and thread: concurrent writers of the same key (two
        # benchmark configurations sending the same query) must not replace each other's file.
        tmp = path.with_name(f"{path.name}.{os.getpid()}.{threading.get_ident()}.tmp")
        tmp.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, path)
