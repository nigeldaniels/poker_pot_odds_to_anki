#!/usr/bin/env python3
"""CLI entrypoint for poker pot-odds question generation and Anki verification."""
from pathlib import Path
import sqlite3
import sys

from poker_odds.cli import main


if __name__ == '__main__':
    try:
        raise SystemExit(main(Path(__file__)))
    except (ValueError, RuntimeError, sqlite3.Error, OSError) as exc:
        print(f'Error: {exc}', file=sys.stderr)
        raise SystemExit(1)
