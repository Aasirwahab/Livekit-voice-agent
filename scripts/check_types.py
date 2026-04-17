#!/usr/bin/env python3
"""Run mypy type checking on the project."""

import subprocess
import sys


def main() -> None:
    """Run mypy type checking."""
    result = subprocess.run(
        ["uv", "run", "mypy", "src/"],
        capture_output=False,
    )
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
