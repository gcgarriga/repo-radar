from __future__ import annotations

import argparse


def non_negative_int(value: str) -> int:
    parsed = int(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("timeout must be non-negative")
    return parsed
