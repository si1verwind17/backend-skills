import os
import subprocess
import time

IMAGE = "gcr.io/google.com/cloudsdktool/google-cloud-cli:emulators"
NAME = "parking-reservation-test-pubsub"
PORT = int(os.environ.get("TEST_PUBSUB_PORT", "55440"))  # host ports 55432-55499 (OI-28)


def _docker(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["docker", *args], capture_output=True, text=True, check=False)


def ensure_running() -> bool:
    """Starts the official Pub/Sub emulator unless it runs; returns True when this call started it."""
    state = _docker("inspect", "-f", "{{.State.Running}}", NAME)
    if state.returncode == 0 and state.stdout.strip() == "true":
        return False
    _docker("rm", "-f", NAME)
    started = _docker(
        "run",
        "-d",
        "--name",
        NAME,
        "-p",
        f"{PORT}:8085",
        IMAGE,
        "gcloud",
        "beta",
        "emulators",
        "pubsub",
        "start",
        "--host-port=0.0.0.0:8085",
        "--project=proj",
    )
    if started.returncode != 0:
        raise RuntimeError(f"cannot start the Pub/Sub emulator: {started.stderr}")
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        if "Server started" in _docker("logs", NAME).stderr + _docker("logs", NAME).stdout:
            return True
        time.sleep(1)
    raise RuntimeError("Pub/Sub emulator did not start")


def stop() -> None:
    _docker("rm", "-f", NAME)
