"""Guard the original suite's collected-test baseline before Tier -1 changes."""

import re
import subprocess
import sys
from pathlib import Path


def test_original_suite_still_collects_25_tests():
    root = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "--collect-only",
            "-q",
            "--ignore=tests/characterization",
        ],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    collected = re.search(r"(\d+) tests? collected", result.stdout)
    assert collected is not None, result.stdout
    assert int(collected.group(1)) == 25
