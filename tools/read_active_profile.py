#!/usr/bin/env python3
"""One-shot K86-1168 identify followed by one yc500 active-profile GET."""
import argparse
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from attackshark_k86.errors import K86Error
from attackshark_k86.protocol import (
    EXPECTED_DEVICE_ID, REPORT_ID, REPORT_LENGTH, decode_yc500_response,
    identify_query, parse_device_id, yc500_queries,
)
from attackshark_k86.transport import K86Client, _descriptor_from_handle
from attackshark_k86.protocol import parse_report_descriptor


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timeout", type=float, default=2.0)
    parser.add_argument("--log", default="docs/06-profile-hardware.jsonl")
    args = parser.parse_args(argv)

    profile_query = yc500_queries()["profile"]()
    expected = bytes([0x85, 0, 0, 0, 0, 0, 0, 0x7A]) + bytes(REPORT_LENGTH - 8)
    if profile_query.encode() != expected:
        parser.error("0x85 codec differs from the reviewed one-shot packet; refusing access")

    client = K86Client(timeout=args.timeout)
    record = {"mode": "hardware", "operation": "yc500_active_profile", "time_unix": time.time(),
              "tx_report_id": REPORT_ID, "query_protocol_hex": expected.hex()}
    try:
        # This opens only the strict built-in 3151:4015/interface-2 selector and
        # validates the HID report descriptor before any Feature Report is sent.
        with client.open() as connection:
            device = connection.device
            record["device"] = {"vid": f"{device.vendor_id:04X}", "pid": f"{device.product_id:04X}",
                                "interface": device.interface_number, "usage_page": f"{device.usage_page:04X}",
                                "usage": f"{device.usage:04X}", "path": str(device.path)}
            descriptor = _descriptor_from_handle(connection.handle, device.path, device)
            record["descriptor"] = parse_report_descriptor(descriptor)

            # Exactly one identify exchange. Any error or unexpected ID stops here.
            identify_raw = connection.feature_roundtrip(identify_query())
            record["identify_tx"] = client.last_exchange.tx_hex if client.last_exchange else identify_query().encode().hex()
            record["identify_rx"] = connection.last_exchange.rx_hex if connection.last_exchange else identify_raw.hex()
            device_id = parse_device_id(identify_raw)
            record["internal_id"] = device_id
            if device_id != EXPECTED_DEVICE_ID:
                raise K86Error(f"expected internal ID {EXPECTED_DEVICE_ID}, received {device_id}; 0x85 not sent")

            # Exactly one configuration GET, enabled only after ID validation.
            raw = connection.feature_roundtrip(profile_query, allow_configuration=True)
            record["profile_tx"] = connection.last_exchange.tx_hex
            record["profile_rx"] = connection.last_exchange.rx_hex
            record["active_profile_index"] = decode_yc500_response(profile_query, raw)
            record["result"] = "success"
    except Exception as exc:
        record["result"] = "error"
        record["error_type"] = type(exc).__name__
        record["error"] = str(exc)
        print(json.dumps(record, sort_keys=True))
        if args.log:
            log_path = Path(args.log)
            if not log_path.is_absolute():
                log_path = ROOT / log_path
            log_path.parent.mkdir(parents=True, exist_ok=True)
            with log_path.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(record, sort_keys=True) + "\n")
        return 1

    print(json.dumps(record, sort_keys=True))
    if args.log:
        log_path = Path(args.log)
        if not log_path.is_absolute():
            log_path = ROOT / log_path
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(record, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
