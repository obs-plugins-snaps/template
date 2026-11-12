"""Fixtures for the e2e tests.

The tests drive the ``e2e-obs`` CLI — from the shared
``obs-plugins-snaps/workflows`` repository — as a subprocess: the CLI is
the harness' stable contract, so these tests keep working across
internal harness refactors.

The session fixture expects the plugin snap to be installed and
connected to the ``obs-studio`` snap. The CI e2e job (``ci.yaml``) does
that; for local runs, follow the instructions in the repository README.
"""

from __future__ import annotations

import os
import subprocess
from collections.abc import Callable
from pathlib import Path

import pytest

#: Seconds allowed for dialogs to appear after an interaction.
WAIT_SECONDS = "10"


def run_e2e(*args: str) -> subprocess.CompletedProcess[str]:
    """Run an ``e2e-obs`` command and return the raw result for assertions.

    The result is never inspected here: tests assert on ``returncode``
    and the captured streams themselves, so a failure shows the actual
    stderr and exit code in the test report.
    """
    return subprocess.run(["e2e-obs", *args], capture_output=True, text=True)


@pytest.fixture(scope="session")
def e2e() -> Callable[..., subprocess.CompletedProcess[str]]:
    """Run an ``e2e-obs`` command (``run_e2e``)."""
    return run_e2e


@pytest.fixture(scope="session")
def obs() -> Path:
    """Start a headless session (sway + OBS) for the whole test run.

    Yields the harness home (``$E2E_OBS_HOME``), where screenshots
    (``shots/``), logs (``logs/``) and state (``.state/``) land.
    """
    run_e2e("start")
    try:
        yield Path(os.environ.get("E2E_OBS_HOME") or os.getcwd()).resolve()
    finally:
        # Nothing raises, so teardown is naturally safe: a failed stop is
        # visible in the harness logs, not as a test error.
        run_e2e("stop")
