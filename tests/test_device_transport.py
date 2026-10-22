import json
from pathlib import Path
import tempfile
import threading
import time
import unittest

from attackshark_k86.device import DeviceInfo, DeviceSelector, select_device
from attackshark_k86.errors import (
    AmbiguousDevice, DeviceDisconnected, DeviceNotFound, DescriptorMismatch,
    IncorrectDevice, IncorrectInterface, MalformedReport, PermissionDenied, TransportError,
    TransportTimeout, UnauthorizedWrite,
)
from attackshark_k86.protocol import identify_query, parse_report_descriptor
from attackshark_k86.transport import (
    HidConnection, K86Client, _descriptor_from_handle, _descriptor_via_sysfs,
    validate_descriptor,
)

ROOT = Path(__file__).resolve().parents[1]
REPORT_DESCRIPTOR = bytes.fromhex("06ffff0902a10175089540b102c0")


def fixture_response():
    with (ROOT / "docs/03-identification-hardware.jsonl").open(encoding="utf-8") as stream:
        record = json.loads(next(line for line in stream if line.strip()))
        return bytes.fromhex(record["response"])


def info(**overrides):
    data = dict(path="/dev/hidraw-random", vendor_id=0x3151, product_id=0x4015,
                interface_number=2, usage_page=0xFFFF, usage=2,
                product_string="Gaming Keyboard", manufacturer_string="ROYUAN", bus_type=1)
    data.update(overrides)
    return DeviceInfo(**data)


class FakeHandle:
    def __init__(self, response=None, exception=None, descriptor=REPORT_DESCRIPTOR, clock=None):
        self.response = response if response is not None else fixture_response()
        self.exception = exception
        self.descriptor = descriptor
        self.sent = []
        self.closed = False

    def get_report_descriptor(self, _size):
        return self.descriptor

    def send_feature_report(self, data):
        self.sent.append(bytes(data))
        return len(data)

    def get_feature_report(self, report_id, size):
        self.requested_read = (report_id, size)
        if self.exception:
            raise self.exception
        return self.response

    def close(self):
        self.closed = True


class FakeBackend:
    def __init__(self, rows=None, handle=None, enumeration_error=None):
        self.rows = rows if rows is not None else [info().__dict__]
        self.handle = handle or FakeHandle()
        self.enumeration_error = enumeration_error
        self.opened_path = None

    def enumerate(self, _vid, _pid):
        if self.enumeration_error:
            raise self.enumeration_error
        return self.rows

    def open_path(self, path):
        self.opened_path = path
        return self.handle


class DeviceAndTransportTests(unittest.TestCase):
    def test_selection_requires_vid_pid_interface_and_usage_descriptor(self):
        chosen = select_device([info()])
        self.assertEqual(chosen.path, "/dev/hidraw-random")
        with self.assertRaises(IncorrectInterface):
            select_device([info(interface_number=1)])
        with self.assertRaises(IncorrectDevice):
            select_device([info(usage_page=1, usage=6)])
        with self.assertRaises(DeviceNotFound):
            select_device([info(product_id=0x4011)])

    def test_composite_keyboard_selects_only_expected_interface_two(self):
        devices = [
            info(path="/dev/hidraw0", interface_number=0, usage_page=1, usage=6),
            info(path="/dev/hidraw1", interface_number=1, usage_page=1, usage=2),
            info(path="/dev/hidraw2", interface_number=2),
        ]
        chosen = select_device(devices)
        self.assertEqual(chosen.path, "/dev/hidraw2")
        self.assertEqual(chosen.interface_number, 2)

        backend = FakeBackend(rows=[device.__dict__ for device in devices])
        with K86Client(backend=backend).open() as connection:
            self.assertEqual(connection.device.interface_number, 2)
        self.assertEqual(backend.opened_path, "/dev/hidraw2")
        self.assertEqual(backend.handle.sent, [])

    def test_interface_two_absent_is_rejected(self):
        with self.assertRaises(IncorrectInterface):
            select_device([info(interface_number=0), info(interface_number=1)])

    def test_multiple_valid_interface_two_candidates_are_ambiguous(self):
        with self.assertRaises(AmbiguousDevice):
            select_device([info(path="/dev/hidraw2a"), info(path="/dev/hidraw2b")])

    def test_wrong_device_and_wrong_interface_two_collection_are_rejected(self):
        with self.assertRaises(DeviceNotFound):
            select_device([info(vendor_id=0x1234)])
        with self.assertRaises(IncorrectDevice):
            select_device([info(interface_number=2, usage_page=1, usage=6)])

    def test_fedora_hidapi_zero_usage_and_empty_strings_use_descriptor_validation(self):
        actual = info(path="1-1.2:1.2", usage_page=0, usage=0,
                      manufacturer_string="", product_string="", bus_type=1)
        self.assertTrue(DeviceSelector().matches(actual))
        self.assertEqual(select_device([actual]), actual)
        validate_descriptor(REPORT_DESCRIPTOR, actual)

        # K86Client still requires the opened handle's descriptor to prove FFFF:0002.
        backend = FakeBackend(rows=[actual.__dict__], handle=FakeHandle())
        with K86Client(backend=backend).open() as connection:
            self.assertEqual(connection.device, actual)
        self.assertEqual(backend.handle.sent, [])

    def test_sysfs_report_descriptor_is_bound_to_same_usb_interface(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "sys"
            usb = root / "devices/platform/usb1/1-1.2"
            interface = usb / "1-1.2:1.2"
            hid_node = interface / "0003:3151:4015.0001"
            usb.mkdir(parents=True)
            interface.mkdir(parents=True)
            hid_node.mkdir()
            bus_devices = root / "bus/usb/devices"
            bus_devices.mkdir(parents=True)
            (bus_devices / "1-1.2").symlink_to(usb)
            (bus_devices / "1-1.2:1.2").symlink_to(interface)
            (usb / "idVendor").write_text("3151\n")
            (usb / "idProduct").write_text("4015\n")
            (interface / "bInterfaceNumber").write_text("02\n")
            (hid_node / "uevent").write_text("HID_ID=0003:00003151:00004015\n")
            (hid_node / "report_descriptor").write_bytes(REPORT_DESCRIPTOR)

            actual = info(path="1-1.2:1.2", usage_page=0, usage=0,
                          manufacturer_string="", product_string="")
            descriptor = _descriptor_via_sysfs(actual.path, actual, root)
            self.assertEqual(descriptor, REPORT_DESCRIPTOR)
            self.assertEqual(_descriptor_from_handle(object(), actual.path, actual, root), REPORT_DESCRIPTOR)
            validate_descriptor(descriptor, actual)

            # The hidraw-style path is resolved dynamically through sysfs links.
            hidraw = root / "class/hidraw/hidraw7"
            hidraw.mkdir(parents=True)
            (hidraw / "device").symlink_to(hid_node)
            actual_by_hidraw = info(path="/dev/hidraw7", usage_page=0, usage=0)
            self.assertEqual(_descriptor_via_sysfs(actual_by_hidraw.path, actual_by_hidraw, root), REPORT_DESCRIPTOR)

    def test_sysfs_descriptor_validation_rejects_wrong_interface_device_or_collection(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "sys"
            usb = root / "devices/platform/usb1/1-1.2"
            interface = usb / "1-1.2:1.2"
            hid_node = interface / "0003:3151:4015.0001"
            usb.mkdir(parents=True)
            interface.mkdir(parents=True)
            hid_node.mkdir()
            bus_devices = root / "bus/usb/devices"
            bus_devices.mkdir(parents=True)
            (bus_devices / "1-1.2").symlink_to(usb)
            (bus_devices / "1-1.2:1.2").symlink_to(interface)
            (usb / "idVendor").write_text("3151\n")
            (usb / "idProduct").write_text("4015\n")
            (interface / "bInterfaceNumber").write_text("01\n")
            (hid_node / "uevent").write_text("HID_ID=0003:00003151:00004015\n")
            (hid_node / "report_descriptor").write_bytes(REPORT_DESCRIPTOR)
            actual = info(path="1-1.2:1.2", usage_page=0, usage=0)
            from attackshark_k86.errors import DescriptorMismatch
            with self.assertRaises(DescriptorMismatch):
                _descriptor_via_sysfs(actual.path, actual, root)
            with self.assertRaises(DescriptorMismatch):
                validate_descriptor(bytes.fromhex("05010906a10175089540b102c0"), actual)

    def test_client_rejects_custom_selector_for_unsupported_devices(self):
        backend = FakeBackend()
        client = K86Client(backend=backend, selector=DeviceSelector(product_id=0x4011))
        with self.assertRaises(IncorrectDevice):
            client.open()
        self.assertIsNone(backend.opened_path)

    def test_client_rejects_selected_record_not_from_current_enumeration(self):
        enumerated = info(path="/dev/hidraw-enumerated")
        backend = FakeBackend(rows=[enumerated.__dict__])
        with self.assertRaises(IncorrectDevice):
            K86Client(backend=backend).open(selected=info(path="/dev/hidraw-stale"))
        self.assertIsNone(backend.opened_path)

    def test_ambiguous_matching_collections_are_rejected(self):
        with self.assertRaises(AmbiguousDevice):
            select_device([info(), info(path="/dev/hidraw-other")])

    def test_usb_bus_is_required_when_reported(self):
        with self.assertRaises(IncorrectDevice):
            select_device([info(bus_type=2)])

    def test_client_sends_one_correct_feature_report_and_closes(self):
        handle = FakeHandle()
        backend = FakeBackend(handle=handle)
        self.assertEqual(K86Client(backend=backend).identify(), 1168)
        self.assertEqual(len(handle.sent), 1)
        self.assertEqual(handle.sent[0][0], 0)  # HID Report ID
        self.assertEqual(handle.sent[0][1:], identify_query().encode())
        self.assertEqual(handle.requested_read, (0, 65))
        self.assertTrue(handle.closed)

    def test_configuration_query_requires_explicit_hardware_authorization(self):
        backend = FakeBackend()
        from attackshark_k86.protocol import yc500_queries
        with self.assertRaises(UnauthorizedWrite):
            K86Client(backend=backend).read_yc500(yc500_queries()["profile"]())
        self.assertIsNone(backend.opened_path)

    def test_connection_requires_explicit_configuration_opt_in_and_validated_id(self):
        from attackshark_k86.protocol import yc500_queries
        handle = FakeHandle()
        connection = HidConnection(handle, info())
        request = yc500_queries()["profile"]()
        with self.assertRaises(UnauthorizedWrite):
            connection.feature_roundtrip(request)
        with self.assertRaises(IncorrectDevice):
            connection.feature_roundtrip(request, allow_configuration=True)
        self.assertEqual(handle.sent, [])
        connection.feature_roundtrip(identify_query())
        # The operation is still rejected because this fixture is only an identify reply;
        # it passes the session guard, but a profile reply must be supplied by a fresh fake.
        self.assertEqual(connection.validated_device_id, 1168)

    def test_descriptor_is_validated_before_any_feature_send(self):
        handle = FakeHandle(descriptor=bytes.fromhex("05010906a101c0"))
        backend = FakeBackend(handle=handle)
        with self.assertRaises(DescriptorMismatch):
            K86Client(backend=backend).identify()
        self.assertEqual(handle.sent, [])
        self.assertTrue(handle.closed)

    def test_incomplete_and_bad_replies_are_rejected(self):
        short = FakeHandle(response=bytes([0x8F, 1, 2]))
        with self.assertRaises(MalformedReport):
            HidConnection(short, info()).feature_roundtrip(identify_query())
        bad = bytearray(fixture_response())
        bad[0] = 0x85
        with self.assertRaises(MalformedReport):
            HidConnection(FakeHandle(response=bad), info()).feature_roundtrip(identify_query())

    def test_transport_timeout_permission_and_disconnect_errors(self):
        with self.assertRaises(TransportTimeout):
            HidConnection(FakeHandle(exception=TimeoutError("deadline")), info()).feature_roundtrip(identify_query())
        with self.assertRaises(PermissionDenied):
            HidConnection(FakeHandle(exception=PermissionError("denied")), info()).feature_roundtrip(identify_query())
        with self.assertRaises(DeviceDisconnected):
            HidConnection(FakeHandle(exception=OSError("No such device")), info()).feature_roundtrip(identify_query())
        with self.assertRaises(TransportError):
            HidConnection(FakeHandle(exception=OSError("control transfer failed")), info()).feature_roundtrip(identify_query())

    def test_disconnected_connection_refuses_io(self):
        connection = HidConnection(FakeHandle(), info())
        connection.close()
        with self.assertRaises(DeviceDisconnected):
            connection.feature_roundtrip(identify_query())

    def test_feature_exchanges_on_one_handle_are_serialized(self):
        entered = threading.Event()
        release = threading.Event()

        class BlockingHandle(FakeHandle):
            def get_feature_report(self, report_id, size):
                entered.set()
                release.wait(1.0)
                return self.response

        handle = BlockingHandle()
        connection = HidConnection(handle, info())
        outcomes = []
        first = threading.Thread(target=lambda: outcomes.append(connection.feature_roundtrip(identify_query())))
        second = threading.Thread(target=lambda: outcomes.append(connection.feature_roundtrip(identify_query())))
        first.start()
        self.assertTrue(entered.wait(0.5))
        second.start()
        time.sleep(0.02)
        self.assertEqual(len(handle.sent), 1)
        release.set()
        first.join(1.0)
        second.join(1.0)
        self.assertFalse(first.is_alive() or second.is_alive())
        self.assertEqual(len(handle.sent), 2)

    def test_client_can_open_a_fresh_session_after_transport_failure(self):
        first_backend = FakeBackend(handle=FakeHandle(exception=OSError("No such device")))
        with self.assertRaises(DeviceDisconnected):
            K86Client(backend=first_backend).identify()
        fresh = FakeBackend(handle=FakeHandle())
        self.assertEqual(K86Client(backend=fresh).identify(), 1168)
        self.assertEqual(fresh.opened_path, info().path)

    def test_elapsed_deadline_is_detected_without_second_exchange(self):
        handle = FakeHandle()
        times = iter([0.0, 1.1, 1.2])
        connection = HidConnection(handle, info(), timeout=1.0, clock=lambda: next(times))
        with self.assertRaises(TransportTimeout):
            connection.feature_roundtrip(identify_query())
        self.assertEqual(len(handle.sent), 1)
        self.assertFalse(hasattr(handle, "requested_read"))


if __name__ == "__main__":
    unittest.main()
