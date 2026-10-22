"""Explicit CLI entry points; no device I/O occurs without a subcommand."""
import argparse
import json
import logging
from pathlib import Path
import sys
import time

from .device import VENDOR_ID, PRODUCT_ID, INTERFACE_NUMBER
from .errors import K86Error
from .protocol import EXPECTED_DEVICE_ID, identify_query, parse_device_id
from .transport import K86Client

ROOT = Path(__file__).resolve().parent.parent
REAL_FIXTURE = ROOT / "docs" / "03-identification-hardware.jsonl"


class JsonFormatter(logging.Formatter):
    def format(self, record):
        fields = getattr(record, "hid_event", None)
        if fields is None:
            fields = {"event": record.getMessage(), "level": record.levelname.lower()}
        return json.dumps(fields, sort_keys=True)


def _read_real_fixture(path: Path = REAL_FIXTURE):
    with path.open(encoding="utf-8") as fixture:
        for line in fixture:
            if line.strip():
                return json.loads(line)
    raise ValueError(f"empty hardware fixture: {path}")


def identify_simulated() -> dict:
    fixture = _read_real_fixture()
    if (fixture.get("vid"), fixture.get("pid"), fixture.get("interface"), fixture.get("report_id"), fixture.get("report_length")) != ("3151", "4015", 2, 0, 64):
        raise ValueError("hardware fixture metadata does not match the validated keyboard")
    response = bytes.fromhex(fixture["response"])
    if fixture.get("command") != identify_query().encode().hex():
        raise ValueError("recorded transmit bytes differ from the 0x8F identify codec")
    device_id = parse_device_id(response)
    return {"mode": "simulation", "vid": "3151", "pid": "4015", "interface": 2,
            "report_id": 0, "report_length": 64, "command": fixture["command"],
            "response": fixture["response"], "internal_id": device_id,
            "catalog_match": device_id == EXPECTED_DEVICE_ID,
            "fixture": str(path_relative(fixture_path=REAL_FIXTURE))}


def path_relative(fixture_path: Path) -> str:
    try:
        return str(fixture_path.relative_to(ROOT))
    except ValueError:
        return str(fixture_path)


def main(argv=None):
    parser = argparse.ArgumentParser(prog="k86-hid", description="Read-only ATTACK SHARK K86 HID identification tools")
    sub = parser.add_subparsers(dest="command", required=True)
    identify = sub.add_parser("identify", help="identify the internal device ID")
    identify.add_argument("--simulate", action="store_true", help="decode the recorded real response without HID access")
    identify.add_argument("--confirm-identify", action="store_true", help="explicitly allow one 0x8F Feature Report exchange")
    identify.add_argument("--timeout", type=float, default=2.0)
    identify.add_argument("--log", help="append result JSON to this JSONL file")
    args = parser.parse_args(argv)

    logger = logging.getLogger("attackshark_k86")
    logger.handlers.clear()
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    try:
        if args.simulate:
            record = identify_simulated()
        else:
            if not args.confirm_identify:
                parser.error("hardware access requires --confirm-identify; no query is sent automatically")
            client = K86Client(timeout=args.timeout)
            device_id = client.identify()
            record = {"mode": "hardware", "vid": f"{VENDOR_ID:04X}", "pid": f"{PRODUCT_ID:04X}",
                      "interface": INTERFACE_NUMBER, "internal_id": device_id,
                      "report_id": 0, "report_length": 64,
                      "catalog_match": device_id == EXPECTED_DEVICE_ID}
            if client.last_exchange is not None:
                record["command"] = client.last_exchange.tx_hex
                record["response"] = client.last_exchange.rx_hex
        record["time_unix"] = time.time()
        print(json.dumps(record, sort_keys=True))
        if args.log:
            with open(args.log, "a", encoding="utf-8") as out:
                out.write(json.dumps(record, sort_keys=True) + "\n")
        return 0 if record["catalog_match"] else 2
    except K86Error as exc:
        logging.getLogger("attackshark_k86").error("operation failed", extra={"hid_event": {"event": "error", "error_type": type(exc).__name__, "message": str(exc)}})
        return 1
    except (OSError, ValueError, KeyError) as exc:
        logging.getLogger("attackshark_k86").error("operation failed", extra={"hid_event": {"event": "error", "error_type": type(exc).__name__, "message": str(exc)}})
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
