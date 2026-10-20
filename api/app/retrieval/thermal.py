"""GPU temperature throttling for indexing.

Why: the laptop's RTX 3050 hit 85-86 C under sustained embedding load and the
machine lost power. `wait_until_cool` lets the indexer pause between batches
until the GPU has cooled back down instead of running flat out.
"""

from __future__ import annotations

import subprocess
import time
from collections.abc import Callable


def gpu_temperature() -> int | None:
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=temperature.gpu", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=10, check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    try:
        return int(result.stdout.strip().splitlines()[0])
    except (ValueError, IndexError):
        return None


def wait_until_cool(max_temp: int, resume_temp: int, poll: float = 5.0,
                    read: Callable[[], int | None] = gpu_temperature,
                    sleep: Callable[[float], None] = time.sleep,
                    max_wait: float = 600.0) -> float:
    """Wait until GPU cools or timeout (max_wait caps total wait time in seconds)."""
    if max_temp <= 0:
        return 0.0
    temp = read()
    if temp is None or temp < max_temp:
        return 0.0
    slept = 0.0
    while slept < max_wait:
        sleep(poll)
        slept += poll
        temp = read()
        if temp is None or temp <= resume_temp:
            return slept
    raise RuntimeError(
        f"GPU still at/above max temp after {slept:g} s; aborting to protect the machine")
