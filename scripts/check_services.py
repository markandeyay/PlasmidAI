from __future__ import annotations

import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_dotenv(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def env(name: str, default: str, dotenv: dict[str, str]) -> str:
    return os.environ.get(name) or dotenv.get(name) or default


def run(command: list[str], *, timeout: int = 30) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
    )


def wait_for_tcp(host: str, port: int, label: str, timeout_seconds: int = 60) -> None:
    deadline = time.monotonic() + timeout_seconds
    last_error: OSError | None = None
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((host, port), timeout=3):
                return
        except OSError as exc:
            last_error = exc
            time.sleep(1)
    raise RuntimeError(f"{label} did not accept TCP connections at {host}:{port}: {last_error}")


def check_docker_compose() -> None:
    if shutil.which("docker") is None:
        raise RuntimeError("docker is not on PATH; install Docker Desktop or Docker Engine.")
    result = run(["docker", "compose", "version"], timeout=15)
    if result.returncode != 0:
        raise RuntimeError(f"`docker compose version` failed:\n{result.stderr.strip()}")


def check_postgres(dotenv: dict[str, str]) -> None:
    host = env("POSTGRES_HOST", "localhost", dotenv)
    port = int(env("POSTGRES_PORT", "5432", dotenv))
    user = env("POSTGRES_USER", "plasmid", dotenv)
    database = env("POSTGRES_DB", "plasmid_design", dotenv)
    wait_for_tcp(host, port, "Postgres")

    ready = run(["docker", "compose", "exec", "-T", "postgres", "pg_isready", "-U", user, "-d", database])
    if ready.returncode != 0:
        raise RuntimeError(f"Postgres pg_isready failed:\n{ready.stderr.strip() or ready.stdout.strip()}")

    vector = run(
        [
            "docker",
            "compose",
            "exec",
            "-T",
            "postgres",
            "psql",
            "-U",
            user,
            "-d",
            database,
            "-tAc",
            "CREATE EXTENSION IF NOT EXISTS vector; SELECT 1 FROM pg_extension WHERE extname = 'vector';",
        ]
    )
    if vector.returncode != 0 or "1" not in vector.stdout:
        raise RuntimeError(f"Postgres pgvector check failed:\n{vector.stderr.strip() or vector.stdout.strip()}")


def check_minio(dotenv: dict[str, str]) -> None:
    endpoint = env("OBJECT_STORE_ENDPOINT", "http://localhost:9000", dotenv).rstrip("/")
    parsed = urllib.parse.urlparse(endpoint)
    host = parsed.hostname or "localhost"
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    wait_for_tcp(host, port, "MinIO")
    try:
        with urllib.request.urlopen(f"{endpoint}/minio/health/live", timeout=10) as response:
            if response.status != 200:
                raise RuntimeError(f"MinIO health endpoint returned HTTP {response.status}")
    except urllib.error.URLError as exc:
        raise RuntimeError(f"MinIO health check failed: {exc}") from exc


def check_redis(dotenv: dict[str, str]) -> None:
    parsed = urllib.parse.urlparse(env("REDIS_URL", "redis://localhost:6379/0", dotenv))
    host = parsed.hostname or "localhost"
    port = parsed.port or 6379
    wait_for_tcp(host, port, "Redis")
    with socket.create_connection((host, port), timeout=5) as connection:
        connection.sendall(b"*1\r\n$4\r\nPING\r\n")
        response = connection.recv(32)
    if not response.startswith(b"+PONG"):
        raise RuntimeError(f"Redis PING failed: {response!r}")


def main() -> int:
    dotenv = load_dotenv(ROOT / ".env")
    checks = [
        ("docker compose", lambda: check_docker_compose()),
        ("postgres + pgvector", lambda: check_postgres(dotenv)),
        ("minio", lambda: check_minio(dotenv)),
        ("redis", lambda: check_redis(dotenv)),
    ]
    for label, check in checks:
        try:
            check()
        except Exception as exc:
            print(f"[FAIL] {label}: {exc}", file=sys.stderr)
            return 1
        print(f"[OK] {label}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
