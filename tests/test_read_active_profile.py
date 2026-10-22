"""CLI integration tests using the real client/transport and a fake HID backend."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from attackshark_k86.transport import K86Client

ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = ROOT / "tools/read_active_profile.py"
SPEC = importlib.util.spec_from_file_location("read_active_profile", TOOL_PATH)
read_active_profile = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(read_active_profile)

DESCRIPTOR = bytes.fromhex("06ffff0902a10175089540b102c0")
IDENTIFY_REPLY = bytes.fromhex(
    "8f90040000000070000000000000000000000000000000000000000000000000"
    "0000000000000000000000000000000000000000000000000000000000000000"
)


class FakeHandle:
    def __init__(self, responses):
        self.responses = list(responses)
        self.sent = []
        self.closed = False

    def get_report_descriptor(self, _size=None):
        return DESCRIPTOR

    def send_feature_report(self, data):
        self.sent.append(bytes(data))
        return len(data)

    def get_feature_report(self, report_id, size):
        if not self.responses:
            raise AssertionError("unexpected extra Feature Report read")
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response

    def close(self):
        self.closed = True


class FakeBackend:
    def __init__(self, handle):
        self.handle = handle
        self.opened_path = None

    def enumerate(self, _vid, _pid):
        return [{
            "path": b"/dev/hidraw-dynamic", "vendor_id": 0x3151,
            "product_id": 0x4015, "interface_number": 2,
            "usage_page": 0xFFFF, "usage": 2, "bus_type": 1,
        }]

    def open_path(self, path):
        self.opened_path = path
        return self.handle


class ReadActiveProfileIntegrationTests(unittest.TestCase):
    def run_cli(self, responses):
        handle = FakeHandle(responses)
        backend = FakeBackend(handle)
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        log_path = Path(temporary.name) / "read.jsonl"
        stdout = io.StringIO()
        with patch.object(read_active_profile, "K86Client",
                          side_effect=lambda timeout: K86Client(backend=backend, timeout=timeout)):
            with contextlib.redirect_stdout(stdout):
                status = read_active_profile.main(["--log", str(log_path)])
        record = json.loads(stdout.getvalue())
        self.assertTrue(handle.closed)
        self.assertEqual(json.loads(log_path.read_text(encoding="utf-8")), record)
        return status, record, handle

    def test_identify_then_profile_records_connection_exchanges_and_success(self):
        profile_reply = bytearray(64)
        profile_reply[0] = 0x85
        profile_reply[1] = 2
        status, record, handle = self.run_cli([IDENTIFY_REPLY, bytes(profile_reply)])

        self.assertEqual(status, 0)
        self.assertEqual(record["result"], "success")
        self.assertEqual(record["internal_id"], 1168)
        self.assertEqual(record["active_profile_index"], 2)
        self.assertEqual(record["identify_tx"], read_active_profile.identify_query().encode().hex())
        self.assertEqual(record["identify_rx"], IDENTIFY_REPLY.hex())
        self.assertEqual(record["profile_tx"], record["query_protocol_hex"])
        self.assertEqual(record["profile_rx"], bytes(profile_reply).hex())
        self.assertEqual([packet[1] for packet in handle.sent], [0x8F, 0x85])
        self.assertEqual(record["identify_outcome"], "ok")
        self.assertEqual(record["profile_outcome"], "ok")

    def test_timeout_records_sent_identify_without_inventing_response_or_success(self):
        status, record, handle = self.run_cli([TimeoutError("simulated timeout")])
        self.assertEqual(status, 1)
        self.assertEqual(record["result"], "error")
        self.assertEqual(record["error_type"], "TransportTimeout")
        self.assertEqual(record["identify_tx"], read_active_profile.identify_query().encode().hex())
        self.assertNotIn("identify_rx", record)
        self.assertEqual(record["identify_outcome"], "timeout")
        self.assertNotIn("profile_tx", record)
        self.assertNotIn("active_profile_index", record)
        self.assertEqual([packet[1] for packet in handle.sent], [0x8F])

    def test_unexpected_internal_id_is_logged_and_stops_before_profile_query(self):
        unexpected = bytearray(IDENTIFY_REPLY)
        unexpected[1:5] = (1234).to_bytes(4, "little")
        status, record, handle = self.run_cli([bytes(unexpected)])
        self.assertEqual(status, 1)
        self.assertEqual(record["result"], "error")
        self.assertEqual(record["internal_id"], 1234)
        self.assertIn("identify_tx", record)
        self.assertIn("identify_rx", record)
        self.assertNotIn("profile_tx", record)
        self.assertNotIn("active_profile_index", record)
        self.assertEqual([packet[1] for packet in handle.sent], [0x8F])


if __name__ == "__main__":
    unittest.main()
