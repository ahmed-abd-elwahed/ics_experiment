"""ICD-11 codes for diagnosis names, from the WHO ICD API.

A name is coded as the first result of the API's flexible search in the ICD-11 MMS
linearization, release 2024-01. Codes are cached on disk by normalized name, including names
that have no match (""), so each name is looked up once.
"""

from __future__ import annotations

import json
import os
import re
import threading
import time
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import httpx

from medsim.errors import ConfigError, MedSimError

TOKEN_URL = "https://icdaccessmanagement.who.int/connect/token"
SEARCH_URL = "https://id.who.int/icd/release/11/2024-01/mms/search"
DEFAULT_CACHE = Path(".icd_cache/icd11_2024-01_mms.json")
_TRAILING = ".,;:!?"


class ICDError(MedSimError):
    """The ICD API could not be reached or refused the request."""


def normalize(name: str) -> str:
    """Lower case, single spaces, no trailing punctuation: the cache key of a name."""
    return re.sub(r"\s+", " ", name.strip().lower()).rstrip(_TRAILING)


def credentials() -> tuple[str, str]:
    client_id = os.environ.get("ICD_CLIENT_ID", "").strip()
    client_secret = os.environ.get("ICD_CLIENT_SECRET", "").strip()
    if not client_id or not client_secret:
        raise ConfigError(
            "ICD_CLIENT_ID and ICD_CLIENT_SECRET are not set. Add your WHO ICD API credentials "
            "(https://icd.who.int/icdapi) to .env."
        )
    return client_id, client_secret


class ICDCoder:
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        *,
        cache_path: Path | None = DEFAULT_CACHE,
        http_client: httpx.Client | None = None,
        workers: int = 10,
        max_retries: int = 5,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._id, self._secret = client_id, client_secret
        self._owns_client = http_client is None
        self._http = http_client or httpx.Client(timeout=20.0)
        self._workers = workers
        self._max_retries = max_retries
        self._sleep = sleep
        self._token: str | None = None
        self._token_lock = threading.Lock()
        self._cache_path = cache_path
        self._cache_lock = threading.Lock()
        self._cache: dict[str, str] = {}
        if cache_path is not None and cache_path.is_file():
            self._cache = json.loads(cache_path.read_text(encoding="utf-8"))

    def close(self) -> None:
        if self._owns_client:
            self._http.close()

    # -- the API --------------------------------------------------------------------------------

    def _refresh_token(self, stale: str | None) -> str:
        with self._token_lock:
            if self._token is None or self._token == stale:
                response = self._http.post(
                    TOKEN_URL,
                    data={
                        "client_id": self._id,
                        "client_secret": self._secret,
                        "scope": "icdapi_access",
                        "grant_type": "client_credentials",
                    },
                )
                if response.status_code >= 400:
                    raise ICDError(f"ICD API token request failed: HTTP {response.status_code}.")
                self._token = str(response.json()["access_token"])
            return self._token

    def _search(self, name: str) -> dict[str, Any]:
        token = self._token or self._refresh_token(None)
        for attempt in range(self._max_retries + 1):
            try:
                response = self._http.get(
                    SEARCH_URL,
                    params={"q": name, "useFlexisearch": "true", "flatResults": "true"},
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Accept": "application/json",
                        "Accept-Language": "en",
                        "API-Version": "v2",
                    },
                )
            except httpx.TransportError as exc:
                error = f"{type(exc).__name__}: {exc}"
            else:
                if response.status_code == 401:
                    token = self._refresh_token(token)
                    continue
                if response.status_code < 400:
                    data: dict[str, Any] = response.json()
                    return data
                error = f"HTTP {response.status_code}"
            if attempt < self._max_retries:
                self._sleep(min(2.0**attempt, 30.0))
        raise ICDError(f"ICD API search for {name!r} failed: {error}.")

    def lookup(self, name: str) -> str:
        """The code of the best match, without the cache; "" when nothing matches."""
        entities = self._search(name).get("destinationEntities") or []
        return str(entities[0].get("theCode") or "") if entities else ""

    # -- cached, in bulk ------------------------------------------------------------------------

    def codes(self, names: Sequence[str]) -> list[str]:
        """One code per name, in order; "" for an empty name or a name with no match."""
        keys = [normalize(name) for name in names]
        missing: dict[str, str] = {}
        for key, name in zip(keys, names, strict=True):
            if key and key not in self._cache:
                missing.setdefault(key, name)
        if missing:
            try:
                with ThreadPoolExecutor(self._workers, thread_name_prefix="icd") as pool:
                    for key, code in zip(
                        missing, pool.map(self._fetch, missing.values()), strict=True
                    ):
                        if code is not None:
                            self._cache[key] = code
            finally:
                self._save()
            failed = [name for key, name in missing.items() if key not in self._cache]
            if failed:
                raise ICDError(
                    f"{len(failed)} of {len(missing)} ICD lookups failed (first: "
                    f"{failed[0]!r}). The others are cached; run again to retry these."
                )
        return [self._cache[key] if key else "" for key in keys]

    def _fetch(self, name: str) -> str | None:
        try:
            return self.lookup(name)
        except ICDError:
            return None  # not cached, so a later run asks again

    def _save(self) -> None:
        if self._cache_path is None:
            return
        with self._cache_lock:
            self._cache_path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self._cache_path.with_name(self._cache_path.name + ".tmp")
            tmp.write_text(json.dumps(self._cache, indent=1, sort_keys=True), encoding="utf-8")
            os.replace(tmp, self._cache_path)
