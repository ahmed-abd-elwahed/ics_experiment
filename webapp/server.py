"""Local web app: edit and run an experiment with live progress, and step through records.

    .venv/bin/python -m webapp            # or double-click run_webapp.command

It serves on 127.0.0.1 only, from the standard library's HTTP server (no extra dependencies).
Requests must name that host, and requests that change anything must send JSON, so other web
pages open in the same browser cannot start experiments.
"""

from __future__ import annotations

import argparse
import json
import logging
import mimetypes
import os
import re
import threading
import uuid
import webbrowser
from collections.abc import Callable
from datetime import UTC, datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlsplit

from pydantic import SecretStr, ValidationError
from pydantic_core import to_jsonable_python

from experiment.config import (
    ExperimentConfig,
    environment_overrides,
    environment_settings,
    initial_information,
    output_path,
    parse_config,
    public_settings,
    select_cases,
)
from experiment.progress import ProgressTracker
from experiment.record import load_record
from experiment.runner import PROJECT_ROOT, ExperimentRunner
from medsim.cli import RedactingFilter
from medsim.config import Settings
from medsim.errors import ConfigError
from strategies import describe_strategies, parse_params
from webapp.environment_runs import (
    is_environment_run,
    list_environment_runs,
    load_environment_runs,
)

logger = logging.getLogger("webapp")

STATIC = Path(__file__).parent / "static"
DEFAULT_PORT = 8765
CONFIG_NAME = re.compile(r"^[\w.-]+\.json$")
RunnerFactory = Callable[..., ExperimentRunner]


class Reply:
    def __init__(self, status: int, body: bytes, content_type: str) -> None:
        self.status = status
        self.body = body
        self.content_type = content_type

    @classmethod
    def json(cls, data: Any, status: int = HTTPStatus.OK) -> Reply:
        return cls(status, json.dumps(data, ensure_ascii=False).encode("utf-8"),
                   "application/json; charset=utf-8")  # fmt: skip

    @classmethod
    def error(cls, status: int, message: str) -> Reply:
        return cls.json({"error": message}, status)


class HTTPError(Exception):
    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status = status


# --- running experiments ------------------------------------------------------------------------


class ExperimentJob:
    """One experiment running in a background thread."""

    def __init__(self, config: ExperimentConfig, runner_factory: RunnerFactory) -> None:
        self.id = uuid.uuid4().hex[:12]
        self.config = config
        self.progress = ProgressTracker()
        self.runner = runner_factory(config, listener=self.progress)
        self.record_path: Path | None = None
        self.thread = threading.Thread(target=self._run, name=f"experiment-{self.id}", daemon=True)

    def _run(self) -> None:
        try:
            plan = self.runner.prepare()  # checks models and loads cases; may raise ConfigError
            self.record_path = plan.output
            add_redaction(plan.settings.openrouter_api_key.get_secret_value())
            self.runner.run()
        except ConfigError as exc:
            self.progress.fail(str(exc))
        except Exception as exc:
            logger.exception("experiment %s failed", self.id)
            self.progress.fail(f"{type(exc).__name__}: {exc}")

    @property
    def running(self) -> bool:
        return self.thread.is_alive()

    def status(self, root: Path) -> dict[str, Any]:
        snapshot = self.progress.snapshot()
        record = None
        if self.record_path is not None:
            record = relative(self.record_path, root)
        return {"id": self.id, "config_name": self.config.name, "record": record, **snapshot}


class RunManager:
    """At most one experiment at a time: they spend API credit and share the rate limits."""

    def __init__(self, runner_factory: RunnerFactory = ExperimentRunner) -> None:
        self._runner_factory = runner_factory
        self._lock = threading.Lock()
        self.job: ExperimentJob | None = None

    def start(self, config: ExperimentConfig) -> ExperimentJob:
        with self._lock:
            if self.job is not None and self.job.running:
                raise HTTPError(HTTPStatus.CONFLICT, "An experiment is already running.")
            job = ExperimentJob(config, self._runner_factory)
            self.job = job
            job.thread.start()
            return job

    def cancel(self) -> bool:
        job = self.job
        if job is None or not job.running:
            return False
        job.runner.cancel()
        return True

    def shutdown(self, timeout: float = 120.0) -> None:
        """Cancel a running experiment and wait for its record to be saved."""
        job = self.job
        if job is not None and job.running:
            print("Stopping the running experiment and saving its record…", flush=True)
            job.runner.cancel()
            job.thread.join(timeout)


# --- the app ------------------------------------------------------------------------------------


def relative(path: Path, root: Path) -> str:
    resolved = path if path.is_absolute() else root / path
    try:
        return resolved.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(resolved)


def settings_in_effect() -> dict[str, Any]:
    """medsim settings as the defaults, .env, and MEDSIM_* variables leave them (no API key),
    for the config editor's reference list."""
    try:
        return public_settings(Settings(openrouter_api_key=SecretStr("unused")))
    except ValidationError:  # an invalid value in .env: list the plain defaults instead
        return {
            name: to_jsonable_python(field.get_default(call_default_factory=True))
            for name, field in Settings.model_fields.items()
            if name != "openrouter_api_key"
        }


def add_redaction(secret: str) -> None:
    """Keep the API key out of log output (once per process)."""
    for handler in logging.getLogger().handlers:
        if not any(isinstance(f, RedactingFilter) for f in handler.filters):
            handler.addFilter(RedactingFilter([secret]))


class App:
    def __init__(self, root: Path = PROJECT_ROOT, runs: RunManager | None = None) -> None:
        self.root = root.resolve()
        self.configs_dir = self.root / "configs"
        self.records_dir = self.root / "records"
        self.cases_dir = self.root / "cases"
        self.runs = runs or RunManager()

    # -- dispatch -------------------------------------------------------------------------------

    def handle(self, method: str, target: str, body: bytes = b"") -> Reply:
        url = urlsplit(target)
        path = url.path
        query = {k: v[-1] for k, v in parse_qs(url.query).items()}
        try:
            if method == "GET":
                return self._get(path, query)
            if method in ("POST", "PUT"):
                data = json.loads(body.decode("utf-8")) if body else None
                return self._post(method, path, data)
            raise HTTPError(HTTPStatus.METHOD_NOT_ALLOWED, f"{method} is not supported.")
        except HTTPError as exc:
            return Reply.error(exc.status, str(exc))
        except json.JSONDecodeError as exc:
            return Reply.error(HTTPStatus.BAD_REQUEST, f"The request body is not JSON: {exc}")
        except ConfigError as exc:
            return Reply.error(HTTPStatus.UNPROCESSABLE_ENTITY, str(exc))

    def _get(self, path: str, query: dict[str, str]) -> Reply:
        if path in ("/", "/index.html"):
            return self._static("index.html")
        if path.startswith("/static/"):
            return self._static(path.removeprefix("/static/"))
        if path == "/api/options":
            return Reply.json(self.options())
        if path.startswith("/api/configs/"):
            return Reply.json(self.read_config(path.removeprefix("/api/configs/")))
        if path == "/api/runs/current":
            job = self.runs.job
            return Reply.json(job.status(self.root) if job else {"state": "idle"})
        if path == "/api/records":
            return Reply.json({"records": self.list_records()})
        if path == "/api/record":
            return self.read_record(query.get("path", ""))
        if path == "/api/environment-runs":
            return Reply.json({"runs": list_environment_runs(self.root)})
        if path == "/api/environment-run":
            return Reply.json(self.read_environment_run(query.get("path", "")))
        raise HTTPError(HTTPStatus.NOT_FOUND, f"Nothing at {path}.")

    def _post(self, method: str, path: str, data: Any) -> Reply:
        if method == "PUT" and path.startswith("/api/configs/"):
            return Reply.json(self.save_config(path.removeprefix("/api/configs/"), data))
        if method == "POST" and path == "/api/validate":
            return Reply.json(self.validate(data))
        if method == "POST" and path == "/api/runs":
            config, plan = self._checked(data)
            job = self.runs.start(config)
            return Reply.json({"id": job.id, "plan": plan}, HTTPStatus.ACCEPTED)
        if method == "POST" and path == "/api/runs/current/cancel":
            return Reply.json({"cancelled": self.runs.cancel()})
        raise HTTPError(HTTPStatus.NOT_FOUND, f"Nothing at {method} {path}.")

    # -- static files ---------------------------------------------------------------------------

    def _static(self, name: str) -> Reply:
        path = (STATIC / name).resolve()
        if not path.is_relative_to(STATIC.resolve()) or not path.is_file():
            raise HTTPError(HTTPStatus.NOT_FOUND, f"No static file {name}.")
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        if content_type.startswith("text/") or content_type.endswith("javascript"):
            content_type += "; charset=utf-8"
        return Reply(HTTPStatus.OK, path.read_bytes(), content_type)

    # -- options and configs --------------------------------------------------------------------

    def options(self) -> dict[str, Any]:
        return {
            "strategies": describe_strategies(),
            "configs": sorted(p.name for p in self.configs_dir.glob("*.json")),
            "case_files": sorted(relative(p, self.root) for p in self.cases_dir.glob("*.json")),
            "environment_settings": settings_in_effect(),
            "initial_information": ["none", "background"],
        }

    def _config_file(self, name: str) -> Path:
        if not CONFIG_NAME.match(name):
            raise HTTPError(HTTPStatus.BAD_REQUEST, "Config names are file names ending in .json.")
        return self.configs_dir / name

    def read_config(self, name: str) -> Any:
        path = self._config_file(name)
        if not path.is_file():
            raise HTTPError(HTTPStatus.NOT_FOUND, f"No config {name}.")
        return json.loads(path.read_text(encoding="utf-8"))

    def save_config(self, name: str, data: Any) -> dict[str, Any]:
        path = self._config_file(name)
        config = parse_config(data)
        path.parent.mkdir(parents=True, exist_ok=True)
        text = json.dumps(config.model_dump(mode="json"), indent=2, ensure_ascii=False)
        path.write_text(text + "\n", encoding="utf-8")
        return {"saved": relative(path, self.root)}

    # -- validation -----------------------------------------------------------------------------

    def _checked(self, data: Any) -> tuple[ExperimentConfig, dict[str, Any]]:
        """Everything that can be checked without spending anything; raises ConfigError."""
        config = parse_config(data)
        cases = select_cases(config)
        for spec in config.strategies:
            parse_params(spec.name, spec.params)
        environment_overrides(config)
        settings = environment_settings(config)  # also catches a missing OPENROUTER_API_KEY
        stopping = config.stopping
        n_runs = len(cases) * len(config.strategies)
        plan = {
            "cases": len(cases),
            "strategies": config.strategy_keys,
            "case_runs": n_runs,
            "max_iterations": stopping.max_iterations * n_runs if stopping.max_iterations else None,
            "workers": min(config.workers, n_runs),
            "output": relative(output_path(config, now=datetime.now(UTC)), self.root),
            "models": settings.stage_models(),
            "first_case": {
                "case_id": cases[0].case_id,
                "initial_information": initial_information(cases[0], config.initial_information),
            },
        }
        return config, plan

    def validate(self, data: Any) -> dict[str, Any]:
        try:
            config, plan = self._checked(data)
        except ConfigError as exc:
            return {"ok": False, "error": str(exc)}
        return {"ok": True, "config": config.model_dump(mode="json"), "plan": plan}

    # -- records --------------------------------------------------------------------------------

    def _record_file(self, path_text: str) -> Path:
        if not path_text:
            raise HTTPError(HTTPStatus.BAD_REQUEST, "Give the record's path.")
        path = Path(path_text)
        path = (path if path.is_absolute() else self.root / path).resolve()
        if not path.is_relative_to(self.root):
            raise HTTPError(HTTPStatus.FORBIDDEN, "Records must be inside the project folder.")
        if path.suffix not in (".json", ".jsonl") or not path.is_file():
            raise HTTPError(HTTPStatus.NOT_FOUND, f"No record at {path_text}.")
        return path

    def list_records(self) -> list[dict[str, Any]]:
        files = {*self.records_dir.rglob("*.json"), *self.records_dir.rglob("*.partial.jsonl")}
        job = self.runs.job
        if job is not None and job.record_path is not None:  # an output outside records/
            for candidate in (job.record_path, job.record_path.with_suffix(".partial.jsonl")):
                path = candidate if candidate.is_absolute() else self.root / candidate
                if path.is_file() and path.resolve().is_relative_to(self.root):
                    files.add(path)
        entries = []
        for path in files:
            stat = path.stat()
            entries.append(
                {
                    "path": relative(path, self.root),
                    "name": path.name,
                    "size": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime, UTC).isoformat(
                        timespec="seconds"
                    ),
                    "partial": path.suffix == ".jsonl",
                }
            )
        return sorted(entries, key=lambda e: e["modified"], reverse=True)

    def read_record(self, path_text: str) -> Reply:
        path = self._record_file(path_text)
        if path.suffix == ".json":
            return Reply(HTTPStatus.OK, path.read_bytes(), "application/json; charset=utf-8")
        try:
            record = load_record(path)
        except ValueError as exc:
            raise HTTPError(HTTPStatus.UNPROCESSABLE_ENTITY, str(exc)) from None
        return Reply(HTTPStatus.OK, record.model_dump_json().encode("utf-8"),
                     "application/json; charset=utf-8")  # fmt: skip

    # -- environment runs -----------------------------------------------------------------------

    def read_environment_run(self, path_text: str) -> dict[str, Any]:
        path = self.root / path_text if path_text else self.root
        if not path_text or not is_environment_run(path, self.root):
            raise HTTPError(HTTPStatus.NOT_FOUND, f"No stored environment run at {path_text!r}.")
        return load_environment_runs(path, self.root)


# --- HTTP ---------------------------------------------------------------------------------------


def make_handler(app: App, allowed_hosts: set[str]) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        server_version = "ics-webapp"

        def _serve(self, method: str) -> None:
            host = (self.headers.get("Host") or "").lower()
            if host not in allowed_hosts:
                reply = Reply.error(HTTPStatus.FORBIDDEN, "Unexpected Host header.")
            elif method != "GET" and not (self.headers.get("Content-Type") or "").startswith(
                "application/json"
            ):
                reply = Reply.error(HTTPStatus.UNSUPPORTED_MEDIA_TYPE, "Send JSON.")
            else:
                length = int(self.headers.get("Content-Length") or 0)
                body = self.rfile.read(length) if length else b""
                reply = app.handle(method, self.path, body)
            self.send_response(reply.status)
            self.send_header("Content-Type", reply.content_type)
            self.send_header("Content-Length", str(len(reply.body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(reply.body)

        def do_GET(self) -> None:
            self._serve("GET")

        def do_POST(self) -> None:
            self._serve("POST")

        def do_PUT(self) -> None:
            self._serve("PUT")

        def log_message(self, format: str, *args: Any) -> None:
            logger.debug("%s %s", self.address_string(), format % args)

    return Handler


def create_server(
    app: App, host: str = "127.0.0.1", port: int = DEFAULT_PORT
) -> ThreadingHTTPServer:
    """Bind ``port``, or the next free one within 20; port 0 picks any free port."""
    last_error: OSError | None = None
    for candidate in [port] if port == 0 else range(port, port + 20):
        try:
            server = ThreadingHTTPServer((host, candidate), make_handler(app, set()))
        except OSError as exc:
            last_error = exc
            continue
        bound = server.server_address[1]
        names = {host, "localhost", "127.0.0.1"}
        server.RequestHandlerClass = make_handler(app, {f"{n}:{bound}" for n in names})
        server.daemon_threads = True
        return server
    raise OSError(f"No free port from {port} to {port + 19}: {last_error}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m webapp",
        description="Web app to run experiments and step through experiment records.",
    )
    parser.add_argument(
        "--port", type=int, default=int(os.environ.get("PORT") or DEFAULT_PORT),
        help=f"Port (default: $PORT, else {DEFAULT_PORT}; the next free one if it is taken).",
    )  # fmt: skip
    parser.add_argument("--no-browser", action="store_true", help="Do not open a browser tab.")
    parser.add_argument("--verbose", action="store_true", help="Debug logging.")
    args = parser.parse_args(argv)

    os.chdir(PROJECT_ROOT)  # .env, the retrieval cache, and config paths are project-relative
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
    )
    app = App(PROJECT_ROOT)
    server = create_server(app, port=args.port)
    url = f"http://127.0.0.1:{server.server_address[1]}/"
    print(f"ICS experiment web app: {url}\nPress Ctrl+C to stop.", flush=True)
    if not args.no_browser:
        threading.Timer(0.6, webbrowser.open, [url]).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        app.runs.shutdown()
        server.server_close()
    return 0
