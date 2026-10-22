#!/usr/bin/env python3
"""Compatibility wrapper; implementation lives in attackshark_k86."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from attackshark_k86.cli import main


def _arguments(argv):
    args = list(argv)
    if not args:
        return ["identify", "--simulate"]
    if "--simulate" in args:
        args.remove("--simulate")
        return ["identify", "--simulate", *args]
    # Translate the cycle-3 explicit hardware confirmation. Selection now
    # uses hidapi metadata and does not accept an arbitrary node path.
    if "--authorize-send" in args:
        index = args.index("--authorize-send")
        if index + 1 >= len(args) or args[index + 1] != "IDENTIFY-3151:4015":
            raise SystemExit("--authorize-send requires IDENTIFY-3151:4015")
        del args[index:index + 2]
        args.append("--confirm-identify")
    if "--device" in args:
        index = args.index("--device")
        del args[index:index + 2]
    return ["identify", *args]


if __name__ == "__main__":
    raise SystemExit(main(_arguments(sys.argv[1:])))
