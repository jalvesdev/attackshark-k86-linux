import json
from pathlib import Path
import unittest

from attackshark_k86.errors import MalformedReport, UnauthorizedWrite
from attackshark_k86.protocol import (
    Checksum, EXPECTED_DEVICE_ID, REPORT_LENGTH, checksum_valid,
    decode_yc500_response, identify_query, parse_device_id,
    parse_report_descriptor, query, yc500_queries,
)

ROOT = Path(__file__).resolve().parents[1]


def hardware_record():
    with (ROOT / "docs/03-identification-hardware.jsonl").open(encoding="utf-8") as stream:
        return json.loads(next(line for line in stream if line.strip()))


class ProtocolTests(unittest.TestCase):
    def setUp(self):
        self.fixture = hardware_record()
        self.response = bytes.fromhex(self.fixture["response"])

    def test_identify_packet_exact_encoding(self):
        packet = identify_query().encode()
        self.assertEqual(len(packet), REPORT_LENGTH)
        self.assertEqual(packet[:8], bytes.fromhex("8f00000000000070"))
        self.assertEqual(packet[8:], bytes(56))
        self.assertEqual(checksum_valid(packet, Checksum.BIT7), True)

    def test_real_fixture_decodes_internal_id_1168(self):
        self.assertEqual(self.fixture["mode"], "hardware")
        self.assertEqual(self.fixture["response"], "8f900400000000700000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000")
        self.assertEqual(parse_device_id(self.response), EXPECTED_DEVICE_ID)
        self.assertEqual(decode_yc500_response(identify_query(), self.response), EXPECTED_DEVICE_ID)

    def test_checksum_validation_and_corruption(self):
        packet = bytearray(identify_query().encode())
        self.assertTrue(checksum_valid(packet, Checksum.BIT7))
        packet[7] ^= 1
        self.assertFalse(checksum_valid(packet, Checksum.BIT7))
        bit8 = bytearray(64)
        bit8[0] = 7
        bit8[8] = (0xFF - (sum(bit8[:8]) & 0xFF)) & 0xFF
        self.assertTrue(checksum_valid(bit8, Checksum.BIT8))

    def test_bad_identify_response_is_rejected(self):
        with self.assertRaises(MalformedReport):
            parse_device_id(self.response[:-1])
        bad_opcode = bytes([0x85]) + self.response[1:]
        with self.assertRaises(MalformedReport):
            parse_device_id(bad_opcode)
        unknown_marker = bytes([0x8F, 0, 0, 0, 0]) + self.response[5:]
        with self.assertRaises(MalformedReport):
            parse_device_id(unknown_marker)

    def test_write_opcode_is_not_encodable(self):
        with self.assertRaises(UnauthorizedWrite):
            query(0x07, "set_led").encode()

    def test_yc500_read_query_codecs(self):
        queries = yc500_queries()
        self.assertEqual(queries["keymap_page"](2, 7).encode()[:3], bytes([0x89, 2, 7]))
        self.assertEqual(queries["fn_page"](1, 0).encode()[:3], bytes([0x90, 1, 0]))
        self.assertEqual(queries["macro_page"](49, 3).encode()[:3], bytes([0x8B, 49, 3]))
        with self.assertRaises(ValueError):
            queries["keymap_page"](0, 8)
        with self.assertRaises(ValueError):
            queries["macro_page"](49, 4)
        with self.assertRaises(ValueError):
            queries["macro_page"](50, 0)

    def test_yc500_reply_decoders(self):
        reply = bytearray(64)
        reply[0:5] = bytes([0x85, 2, 0, 0, 0])
        self.assertEqual(decode_yc500_response(yc500_queries()["profile"](), reply), 2)
        reply[0] = 0x92
        reply[1:9] = bytes([1, 0, 2, 0, 3, 0, 4, 0])
        self.assertEqual(decode_yc500_response(yc500_queries()["sleep_timers"](), reply), (1, 2, 3, 4))

    def test_all_documented_query_fixtures_are_synthetic_and_decode(self):
        q = yc500_queries()
        # Synthetic protocol-shaped fixtures; none are recordings from the keyboard.
        fixtures = {
            "revision": (q["revision"](), [0x80, 0x34, 0x12], 0x1234),
            "profile": (q["profile"](), [0x85, 2], 2),
            "options": (q["options"](), [0x86, 0, 0x81, 1, 1], {"flags": 0x81, "fn_matrix": 1, "power_save": 1}),
            "led_params": (q["led_params"](), [0x87, 1, 2, 3, 4, 5, 6, 7], {"mode": 1, "speed": 2, "brightness": 3, "option_flags": 4, "rgb": (5, 6, 7)}),
            "side_led_params": (q["side_led_params"](), [0x88, 1, 2, 3, 4, 5, 6, 7], {"mode": 1, "speed": 2, "brightness": 3, "option_flags": 4, "rgb": (5, 6, 7)}),
            "keymap_page": (q["keymap_page"](0, 0), [0] * 64, bytes(64)),
            "macro_page": (q["macro_page"](0, 0), [0] * 64, bytes(64)),
            "userpic": (q["userpic"](), [0x8C] + [0] * 63, bytes([0x8C] + [0] * 63)),
            "fn_page": (q["fn_page"](0, 0), [0] * 64, bytes(64)),
            "debounce": (q["debounce"](), [0x91, 0, 5], 5),
            "sleep_timers": (q["sleep_timers"](), [0x92, 1, 0, 2, 0, 3, 0, 4, 0], (1, 2, 3, 4)),
            "auto_os": (q["auto_os"](), [0x97, 1], True),
        }
        for name, (request, prefix, expected) in fixtures.items():
            with self.subTest(operation=name):
                report = bytes(prefix) + bytes(64 - len(prefix))
                self.assertEqual(decode_yc500_response(request, report), expected)

    def test_query_family_and_parameters_fail_closed(self):
        with self.assertRaises(UnauthorizedWrite):
            query(0x84, "gen2_profile").encode()
        with self.assertRaises(UnauthorizedWrite):
            query(0x85, "wrong_family", family="gen2").encode()
        queries = yc500_queries()
        for args in [(-1, 0), (256, 0), (0, -1), (0, 8)]:
            with self.subTest(args=args), self.assertRaises(ValueError):
                queries["keymap_page"](*args)

    def test_invalid_query_checksum_and_unexpected_values(self):
        packet = bytearray(identify_query().encode())
        packet[7] ^= 1
        self.assertFalse(checksum_valid(packet, Checksum.BIT7))
        with self.assertRaises(MalformedReport):
            decode_yc500_response(yc500_queries()["revision"](), bytes([0x85]) + bytes(63))
        for name, opcode, index, value in [("debounce", 0x91, 2, 0), ("debounce", 0x91, 2, 11), ("auto_os", 0x97, 1, 2)]:
            response = bytearray(64)
            response[0] = opcode
            response[index] = value
            with self.subTest(name=name, value=value), self.assertRaises(MalformedReport):
                decode_yc500_response(yc500_queries()[name](), response)

    def test_descriptor_parser_recognizes_expected_collection_and_feature(self):
        descriptor = bytes.fromhex("06ffff0902a10175089540b102c0")
        parsed = parse_report_descriptor(descriptor)
        self.assertEqual(parsed["usage_page"], 0xFFFF)
        self.assertEqual(parsed["usage"], 2)
        self.assertEqual(parsed["report_id_0_feature_bytes"], 64)
        self.assertTrue(parsed["has_report_id_0_feature_64"])


if __name__ == "__main__":
    unittest.main()
