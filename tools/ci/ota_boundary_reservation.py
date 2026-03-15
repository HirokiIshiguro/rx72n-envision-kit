#!/usr/bin/env python3
"""Manage a per-device OTA boundary reservation across split CI jobs.

The legacy OTA flow spans Raspberry Pi jobs (`prepare_ota`, `ota_monitor`) and
Windows jobs (`ota_create_job`, `ota_finalize`). A simple per-job lock is not
enough because another pipeline can reflash the device or replace the AWS OTA
job in the gap between those jobs.

This helper stores a small lease file on the Raspberry Pi that owns the target
device. Raspberry Pi jobs operate on that file locally. Windows jobs reach the
same file over SSH to assert or release the reservation.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any


DEFAULT_STATE_DIR = "/tmp/gitlab-ota-boundary-shared"
DEFAULT_TIMEOUT = 1800
DEFAULT_POLL_INTERVAL = 5.0
DEFAULT_STALE_SECONDS = 1800
DEFAULT_LOCK_TIMEOUT = 30


def default_state_dir() -> str:
    if os.name == "nt":
        return str(Path(tempfile.gettempdir()) / "gitlab-ota-boundary")
    return DEFAULT_STATE_DIR


def iso_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def owner_summary(state: dict[str, Any] | None) -> str:
    if not state:
        return "<none>"
    owner = state.get("owner", "<unknown>")
    pipeline_id = state.get("pipeline_id")
    ref = state.get("ref")
    touched_at = state.get("touched_at")
    extra = []
    if pipeline_id:
        extra.append(f"pipeline={pipeline_id}")
    if ref:
        extra.append(f"ref={ref}")
    if touched_at:
        extra.append(f"touched_at={touched_at}")
    suffix = f" ({', '.join(extra)})" if extra else ""
    return f"{owner}{suffix}"


class LockTimeoutError(RuntimeError):
    pass


class SimpleFileLock:
    """Portable lock using O_EXCL file creation."""

    def __init__(self, path: Path, timeout: int) -> None:
        self.path = path
        self.timeout = timeout
        self.fd: int | None = None

    def __enter__(self) -> "SimpleFileLock":
        ensure_shared_dir(self.path.parent)
        deadline = time.time() + self.timeout
        while True:
            try:
                self.fd = os.open(
                    str(self.path),
                    os.O_CREAT | os.O_EXCL | os.O_WRONLY,
                    0o600,
                )
                payload = f"{os.getpid()} {iso_now()}\n".encode("utf-8")
                os.write(self.fd, payload)
                return self
            except FileExistsError:
                if self.path.exists():
                    age = time.time() - self.path.stat().st_mtime
                    if age > self.timeout:
                        print(
                            f"[LEASE] Removing stale mutex {self.path} (age={age:.0f}s)",
                            flush=True,
                        )
                        try:
                            self.path.unlink()
                            continue
                        except FileNotFoundError:
                            continue
                if time.time() >= deadline:
                    raise LockTimeoutError(
                        f"Timed out waiting for mutex: {self.path}"
                    )
                time.sleep(0.2)

    def __exit__(self, exc_type, exc, tb) -> None:
        if self.fd is not None:
            os.close(self.fd)
            self.fd = None
        try:
            self.path.unlink()
        except FileNotFoundError:
            pass


def read_state(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        with path.open(encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        print(f"[LEASE] Warning: corrupt lease file detected: {path}", flush=True)
        return {"corrupt": True}


def write_state(path: Path, payload: dict[str, Any]) -> None:
    ensure_shared_dir(path.parent)
    tmp = path.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
        f.write("\n")
    os.replace(tmp, path)


def state_is_stale(state: dict[str, Any], stale_seconds: int) -> bool:
    if state.get("corrupt"):
        return True
    touched_raw = state.get("touched_epoch") or state.get("acquired_epoch")
    try:
        touched_epoch = float(touched_raw)
    except (TypeError, ValueError):
        return True
    return (time.time() - touched_epoch) > stale_seconds


def ensure_shared_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    try:
        # Allow both gitlab-runner and admin (SSH from Windows jobs) to update
        # the same lease directory on the Raspberry Pi.
        os.chmod(path, 0o1777)
    except PermissionError:
        pass


def build_payload(args: argparse.Namespace, previous: dict[str, Any] | None) -> dict[str, Any]:
    now_epoch = time.time()
    acquired_epoch = now_epoch
    acquired_at = iso_now()
    if previous and previous.get("owner") == args.owner:
        acquired_epoch = float(previous.get("acquired_epoch", now_epoch))
        acquired_at = previous.get("acquired_at", acquired_at)
    return {
        "device_id": args.device_id,
        "owner": args.owner,
        "project_id": args.project_id,
        "pipeline_id": args.pipeline_id,
        "pipeline_url": args.pipeline_url,
        "ref": args.ref,
        "acquired_at": acquired_at,
        "acquired_epoch": acquired_epoch,
        "touched_at": iso_now(),
        "touched_epoch": now_epoch,
    }


def operate_locally(args: argparse.Namespace) -> int:
    state_dir = Path(args.state_dir)
    lease_path = state_dir / f"{args.device_id}.json"
    mutex_path = state_dir / f"{args.device_id}.lock"

    def locked_read() -> dict[str, Any] | None:
        state = read_state(lease_path)
        if state and state.get("corrupt"):
            print(f"[LEASE] Removing corrupt lease file: {lease_path}", flush=True)
            try:
                lease_path.unlink()
            except FileNotFoundError:
                pass
            return None
        return state

    if args.action == "acquire":
        deadline = time.time() + args.timeout
        while True:
            with SimpleFileLock(mutex_path, args.lock_timeout):
                current = locked_read()
                if current is None or current.get("owner") == args.owner:
                    payload = build_payload(args, current)
                    write_state(lease_path, payload)
                    print(
                        f"[LEASE] Acquired {args.device_id} for {args.owner}",
                        flush=True,
                    )
                    return 0
                if state_is_stale(current, args.stale_seconds):
                    print(
                        f"[LEASE] Stealing stale lease on {args.device_id} from {owner_summary(current)}",
                        flush=True,
                    )
                    payload = build_payload(args, None)
                    write_state(lease_path, payload)
                    return 0
                remaining = deadline - time.time()
                print(
                    f"[LEASE] Waiting for {args.device_id}; owned by {owner_summary(current)}",
                    flush=True,
                )
            if remaining <= 0:
                print(
                    f"[LEASE] Timeout while waiting for reservation on {args.device_id}",
                    file=sys.stderr,
                    flush=True,
                )
                return 1
            time.sleep(min(args.poll_interval, max(0.5, remaining)))

    with SimpleFileLock(mutex_path, args.lock_timeout):
        current = locked_read()
        if args.action == "assert":
            if current is None:
                print(
                    f"[LEASE] No active reservation for {args.device_id}",
                    file=sys.stderr,
                    flush=True,
                )
                return 1
            if current.get("owner") != args.owner:
                print(
                    f"[LEASE] Reservation mismatch on {args.device_id}: expected {args.owner}, got {owner_summary(current)}",
                    file=sys.stderr,
                    flush=True,
                )
                return 1
            payload = build_payload(args, current)
            write_state(lease_path, payload)
            print(
                f"[LEASE] Verified reservation on {args.device_id} for {args.owner}",
                flush=True,
            )
            return 0

        if args.action == "release":
            if current is None:
                print(
                    f"[LEASE] Nothing to release for {args.device_id}",
                    flush=True,
                )
                return 0
            if current.get("owner") != args.owner:
                print(
                    f"[LEASE] Refusing to release {args.device_id}; owned by {owner_summary(current)}",
                    file=sys.stderr,
                    flush=True,
                )
                return 1
            try:
                lease_path.unlink()
            except FileNotFoundError:
                pass
            print(
                f"[LEASE] Released {args.device_id} for {args.owner}",
                flush=True,
            )
            return 0

    print(f"[LEASE] Unsupported action: {args.action}", file=sys.stderr, flush=True)
    return 2


def detect_identity_file(explicit: str | None) -> str | None:
    if explicit:
        return explicit
    candidates = []
    home = Path.home()
    candidates.append(home / ".ssh" / "id_ed25519")
    userprofile = os.environ.get("USERPROFILE")
    if userprofile:
        candidates.append(Path(userprofile) / ".ssh" / "id_ed25519")
    for path in candidates:
        if path.is_file():
            return str(path)
    return None


def null_known_hosts() -> str:
    return "NUL" if os.name == "nt" else "/dev/null"


def run_over_ssh(args: argparse.Namespace) -> int:
    target = f"{args.user}@{args.host}"
    identity = detect_identity_file(args.identity_file)
    cmd = [
        "ssh",
        "-o",
        "BatchMode=yes",
        "-o",
        "StrictHostKeyChecking=no",
        "-o",
        f"UserKnownHostsFile={null_known_hosts()}",
    ]
    if identity:
        cmd.extend(["-i", identity])
    cmd.extend(
        [
            target,
            "python3",
            "-",
            "--internal-remote-helper",
            "--action",
            args.action,
            "--device-id",
            args.device_id,
            "--owner",
            args.owner,
            "--state-dir",
            args.state_dir,
            "--timeout",
            str(args.timeout),
            "--poll-interval",
            str(args.poll_interval),
            "--stale-seconds",
            str(args.stale_seconds),
            "--lock-timeout",
            str(args.lock_timeout),
        ]
    )
    if args.project_id:
        cmd.extend(["--project-id", args.project_id])
    if args.pipeline_id:
        cmd.extend(["--pipeline-id", args.pipeline_id])
    if args.pipeline_url:
        cmd.extend(["--pipeline-url", args.pipeline_url])
    if args.ref:
        cmd.extend(["--ref", args.ref])

    payload = Path(__file__).read_text(encoding="utf-8")
    print(f"[LEASE] Remote {args.action} on {target} for {args.device_id}", flush=True)
    result = subprocess.run(cmd, input=payload, text=True)
    return result.returncode


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Reserve the split OTA boundary for a specific DEVICE_ID"
    )
    parser.add_argument(
        "--action",
        choices=("acquire", "assert", "release"),
        required=True,
        help="Lease operation to perform",
    )
    parser.add_argument("--device-id", required=True, help="Target DEVICE_ID")
    parser.add_argument(
        "--owner",
        required=True,
        help="Stable owner string, typically project/pipeline/device",
    )
    parser.add_argument(
        "--state-dir",
        default=default_state_dir(),
        help="Directory that stores lease files",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT,
        help="Max seconds to wait while acquiring a busy lease",
    )
    parser.add_argument(
        "--poll-interval",
        type=float,
        default=DEFAULT_POLL_INTERVAL,
        help="Sleep interval while waiting for a busy lease",
    )
    parser.add_argument(
        "--stale-seconds",
        type=int,
        default=DEFAULT_STALE_SECONDS,
        help="Steal the lease if it has not been touched for this many seconds",
    )
    parser.add_argument(
        "--lock-timeout",
        type=int,
        default=DEFAULT_LOCK_TIMEOUT,
        help="Timeout for the short mutex around lease file updates",
    )
    parser.add_argument("--project-id", default="", help="CI project id for metadata")
    parser.add_argument("--pipeline-id", default="", help="CI pipeline id for metadata")
    parser.add_argument("--pipeline-url", default="", help="CI pipeline url for metadata")
    parser.add_argument("--ref", default="", help="CI ref name for metadata")
    parser.add_argument("--host", default="", help="Operate on a remote Raspberry Pi over SSH")
    parser.add_argument("--user", default="admin", help="SSH user for remote mode")
    parser.add_argument(
        "--identity-file",
        default="",
        help="Optional SSH private key path for remote mode",
    )
    parser.add_argument(
        "--internal-remote-helper",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.host and not args.internal_remote_helper:
        return run_over_ssh(args)
    return operate_locally(args)


if __name__ == "__main__":
    sys.exit(main())
