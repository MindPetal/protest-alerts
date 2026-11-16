"""
Entry point: read the run mode and settings, then run the search.
"""

import argparse
import logging

from protest_alerts import search
from protest_alerts.config import MODES, Settings


def run(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="protest-alerts",
        description="Post GAO protest updates for tracked solicitations.",
    )
    parser.add_argument(
        "mode",
        choices=MODES,
        help="daily: protests filed or decided yesterday. "
        "roundup: all currently open protests.",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO)
    search.main(Settings.from_env(mode=args.mode))


if __name__ == "__main__":
    run()
