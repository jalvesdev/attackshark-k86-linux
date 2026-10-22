"""hidapi transport with a narrow allow-list and structured logs."""
import logging
import errno
import os
from pathlib import Path
import re
import sys
import threading
import time
from dataclasses import asdict, dataclass
from typing import Any

from .device import (DeviceInfo, DeviceSelector, VENDOR_USAGE, VENDOR_USAGE_PAGE,
                     discover_devices, select_device)
from .errors import (DeviceDisconnected, DeviceOpenError, DescriptorMismatch, HidApiUnavailable,
                     K86Error,
                     IncorrectDevice, MalformedReport, PermissionDenied,
                     TransportError, TransportTimeout, UnauthorizedWrite)
from .protocol import (EXPECTED_DEVICE_ID, READ_OPCODES, REPORT_ID, REPORT_LENGTH,
                       Query, decode_yc500_response, identify_query,
                       parse_device_id, parse_report_descriptor)

logger = logging.getLogger("attackshark_k86")


@dataclass(frozen=True)
class ExchangeRecord:
    event: str
    opcode: int
    report_id: int
    report_length: int
    elapsed_ms: float
    tx_hex: str
    rx_hex: str | None
    outcome: str


class HidApiBackend:
    """Thin adapter selecting the native hidraw backend on Linux."""
    def __init__(self, module: Any | None = None):
        if module is None:
            try:
                if sys.platform.startswith("linux"):
                    # The `hid` extension in some Python wheels is built with
                    # libusb. A hidraw udev ACL does not grant USBFS access;
                    # the same hidapi distribution also ships the `hidraw`
                    # extension, which enumerates dynamic /dev/hidrawN paths.
                    import hidraw as module  # type: ignore[no-redef]
                else:
                    import hid as module  # type: ignore[no-redef]
            except ImportError as exc:
                backend = "hidraw backend (hidapi>=0.15)" if sys.platform.startswith("linux") else "hidapi (import name: hid)"
                raise HidApiUnavailable(f"install the Python {backend}") from exc
        self.module = module

    def enumerate(self, vendor_id: int, product_id: int):
        return self.module.enumerate(vendor_id, product_id)

    def open_path(self, path: Any):
        dev = self.module.device()
        try:
            dev.open_path(path)
        except OSError as exc:
            detail = ""
            error_getter = getattr(dev, "error", None)
            if error_getter is not None:
                try:
                    detail = str(error_getter() or "")
                except Exception:
                    pass
            raise _classify_open_error(path, exc, detail) from exc
        return dev


def _classify_open_error(path: Any, exc: OSError, backend_detail: str = "") -> K86Error:
    detail = backend_detail.strip() or str(exc).strip() or type(exc).__name__
    message = detail.lower()
    if isinstance(exc, PermissionError) or exc.errno in (errno.EACCES, errno.EPERM) or any(
            marker in message for marker in ("permission denied", "access denied", "operation not permitted")):
        return PermissionDenied(f"permission denied opening selected HID path {path!r}: {detail}")
    if exc.errno in (errno.ENOENT, errno.ENODEV, errno.ENXIO) or any(
            marker in message for marker in ("no such device", "no such file or directory", "device not connected")):
        return DeviceDisconnected(f"selected HID path {path!r} disappeared during open: {detail}")
    return DeviceOpenError(f"could not open selected HID path {path!r}: {detail}")


def _descriptor_from_handle(handle: Any, path: Any | None = None,
                            device: DeviceInfo | None = None,
                            sysfs_root: Path = Path("/sys")) -> bytes:
    getter = getattr(handle, "get_report_descriptor", None)
    if getter is not None:
        output_buffer = bytearray(4096)
        calls = (lambda: getter(), lambda: getter(4096), lambda: getter(output_buffer))
        for index, invoke in enumerate(calls):
            try:
                result = invoke()
            except TypeError:
                continue
            if isinstance(result, tuple):
                result = result[0]
            if isinstance(result, int):
                if result < 0:
                    raise DescriptorMismatch("could not read HID report descriptor")
                if index == 2 and 0 < result <= len(output_buffer):
                    descriptor = bytes(output_buffer[:result])
                    if descriptor:
                        return descriptor
                continue
            if result is None:
                continue
            try:
                descriptor = bytes(result)
                if descriptor and len(descriptor) <= 4096:
                    return descriptor
            except (TypeError, ValueError):
                pass
    # Some Python hidapi bindings omit hid_get_report_descriptor. On Linux,
    # read the raw descriptor from sysfs and prove that its HID node belongs to
    # the exact USB interface represented by the enumerated path.
    if sys.platform.startswith("linux") and path is not None:
        if device is None:
            raise DescriptorMismatch("cannot validate sysfs descriptor without selected VID:PID/interface metadata")
        return _descriptor_via_sysfs(path, device, sysfs_root)
    raise DescriptorMismatch("hidapi binding cannot provide the report descriptor; refusing an unverified collection")


_USB_INTERFACE_NAME = re.compile(r"^\d+-[^/]+:\d+\.\d+$")
_HIDRAW_NAME = re.compile(r"^hidraw\d+$")


def _sysfs_interface_and_hid_node(path: Any, device: DeviceInfo,
                                  sysfs_root: Path = Path("/sys")) -> tuple[Path, Path]:
    """Resolve an enumerated hidapi path to its same-device sysfs HID node."""
    raw_path = os.fsdecode(path)
    interface: Path | None = None
    hid_node: Path | None = None

    # Some hidapi builds expose the USB interface sysname; standard hidraw
    # builds commonly expose /dev/hidrawN. Both are resolved dynamically.
    if _USB_INTERFACE_NAME.fullmatch(raw_path):
        candidate = sysfs_root / "bus" / "usb" / "devices" / raw_path
        if candidate.exists():
            interface = candidate.resolve(strict=True)
    elif Path(raw_path).name.startswith("hidraw") and _HIDRAW_NAME.fullmatch(Path(raw_path).name):
        hidraw_link = sysfs_root / "class" / "hidraw" / Path(raw_path).name / "device"
        try:
            hid_node = hidraw_link.resolve(strict=True)
        except OSError as exc:
            raise DescriptorMismatch(f"cannot resolve enumerated HID path {raw_path} through sysfs: {exc}") from exc
        interface = next((parent for parent in hid_node.parents
                          if _USB_INTERFACE_NAME.fullmatch(parent.name)
                          and (parent / "bInterfaceNumber").is_file()), None)

    if interface is None:
        raise DescriptorMismatch(
            f"cannot map enumerated HID path {raw_path!r} to a USB interface in sysfs; "
            "usage metadata is insufficient, so refusing to open an unverified collection"
        )

    try:
        interface_number = int((interface / "bInterfaceNumber").read_text(encoding="ascii").strip(), 16)
        usb_parent = interface.parent
        vendor_id = int((usb_parent / "idVendor").read_text(encoding="ascii").strip(), 16)
        product_id = int((usb_parent / "idProduct").read_text(encoding="ascii").strip(), 16)
    except PermissionError as exc:
        raise PermissionDenied(f"cannot read USB identity metadata for {interface}: {exc}") from exc
    except (OSError, ValueError) as exc:
        raise DescriptorMismatch(f"incomplete USB identity metadata at {interface}: {exc}") from exc

    if (vendor_id, product_id, interface_number) != (
            device.vendor_id, device.product_id, device.interface_number):
        raise DescriptorMismatch(
            f"sysfs interface identity {vendor_id:04X}:{product_id:04X}/interface {interface_number} "
            f"does not match enumerated {device.vendor_id:04X}:{device.product_id:04X}/interface {device.interface_number}"
        )

    if hid_node is None:
        # With a sysfs interface path, select a HID child only when its uevent
        # confirms the same USB bus, VID and PID. Never accept an arbitrary
        # report_descriptor found elsewhere under sysfs.
        children = [child for child in interface.iterdir() if child.is_dir()]
        matching: list[Path] = []
        for child in children:
            try:
                attrs = _parse_uevent(child / "uevent")
            except (OSError, UnicodeError):
                continue
            if _hid_uevent_matches(attrs, device):
                matching.append(child.resolve(strict=True))
        if len(matching) != 1:
            raise DescriptorMismatch(
                f"expected one sysfs HID child for {device.vendor_id:04X}:{device.product_id:04X} "
                f"on interface {device.interface_number}, found {len(matching)}"
            )
        hid_node = matching[0]
    else:
        try:
            attrs = _parse_uevent(hid_node / "uevent")
        except (OSError, UnicodeError) as exc:
            raise DescriptorMismatch(f"cannot verify HID sysfs node identity {hid_node}: {exc}") from exc
        if not _hid_uevent_matches(attrs, device):
            raise DescriptorMismatch(f"sysfs HID node {hid_node} does not match the selected USB device")

    # Ensure the resolved HID node is actually below the verified USB interface.
    try:
        hid_node.relative_to(interface)
    except ValueError as exc:
        raise DescriptorMismatch(f"HID sysfs node {hid_node} is outside selected interface {interface}") from exc
    descriptor_path = hid_node / "report_descriptor"
    try:
        descriptor = descriptor_path.read_bytes()
    except PermissionError as exc:
        raise PermissionDenied(f"cannot read report descriptor {descriptor_path}: {exc}") from exc
    except OSError as exc:
        raise DescriptorMismatch(f"cannot read same-interface sysfs report descriptor {descriptor_path}: {exc}") from exc
    if not descriptor or len(descriptor) > 4096:
        raise DescriptorMismatch(f"invalid sysfs report descriptor size {len(descriptor)} at {descriptor_path}")
    return interface, descriptor


def _parse_uevent(path: Path) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in path.read_text(encoding="ascii").splitlines():
        key, separator, value = line.partition("=")
        if separator:
            fields[key] = value
    return fields


def _hid_uevent_matches(fields: dict[str, str], device: DeviceInfo) -> bool:
    hid_id = fields.get("HID_ID", "").split(":")
    if len(hid_id) != 3:
        return False
    try:
        bus, vendor_id, product_id = (int(value, 16) for value in hid_id)
    except ValueError:
        return False
    return (bus, vendor_id, product_id) == (0x0003, device.vendor_id, device.product_id)


def _descriptor_via_sysfs(path: Any, device: DeviceInfo, sysfs_root: Path = Path("/sys")) -> bytes:
    _, descriptor = _sysfs_interface_and_hid_node(path, device, sysfs_root)
    return descriptor


def validate_descriptor(descriptor: bytes, device: DeviceInfo) -> None:
    parsed = parse_report_descriptor(descriptor)
    expected_usage = (VENDOR_USAGE_PAGE, VENDOR_USAGE)
    reported_usage = (device.usage_page, device.usage)
    if reported_usage != (0, 0) and reported_usage != expected_usage:
        raise DescriptorMismatch(
            f"hidapi reported collection {reported_usage[0]:04X}:{reported_usage[1]:04X}, "
            f"expected {expected_usage[0]:04X}:{expected_usage[1]:04X}"
        )
    if (parsed["usage_page"], parsed["usage"]) != expected_usage:
        raise DescriptorMismatch(
            f"selected interface descriptor declares collection "
            f"{parsed['usage_page']:04X}:{parsed['usage']:04X}, expected FFFF:0002"
        )
    if not parsed["has_report_id_0_feature_64"]:
        raise DescriptorMismatch("interface descriptor does not declare a 64-byte Feature Report with ID 0")


class HidConnection:
    def __init__(self, handle: Any, device: DeviceInfo, timeout: float = 1.0, clock=time.monotonic):
        if timeout <= 0:
            raise ValueError("timeout must be positive")
        self.handle = handle
        self.device = device
        self.timeout = timeout
        self.clock = clock
        self.closed = False
        self.last_exchange: ExchangeRecord | None = None
        self._exchange_lock = threading.Lock()
        self.validated_device_id: int | None = None

    def close(self):
        with self._exchange_lock:
            if not self.closed:
                self.closed = True
                try:
                    self.handle.close()
                except OSError as exc:
                    logger.warning("HID close error", extra={"event": "close_error", "error": str(exc)})

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        self.close()

    def feature_roundtrip(self, request: Query, *, allow_configuration: bool = False) -> bytes:
        # hidapi handles are not assumed to support concurrent feature exchanges.
        with self._exchange_lock:
            if request.opcode != 0x8F:
                if not allow_configuration:
                    raise UnauthorizedWrite("configuration GET requires explicit allow_configuration=True")
                if self.validated_device_id != EXPECTED_DEVICE_ID:
                    raise IncorrectDevice("configuration GET requires a validated K86-1168 identify response")
            result = self._feature_roundtrip(request)
            if request.opcode == 0x8F:
                self.validated_device_id = parse_device_id(result)
            return result

    def _feature_roundtrip(self, request: Query) -> bytes:
        if self.closed:
            raise DeviceDisconnected("HID connection is closed")
        if request.opcode not in READ_OPCODES:
            raise UnauthorizedWrite(f"opcode 0x{request.opcode:02X} is not an allowed GET")
        packet = request.encode()
        if len(packet) != REPORT_LENGTH or packet[0] != request.opcode:
            raise MalformedReport("invalid outgoing Feature Report")
        tx = bytes((REPORT_ID,)) + packet
        started = self.clock()
        try:
            sent = self.handle.send_feature_report(list(tx))
            if sent is not None and sent < len(tx):
                raise MalformedReport(f"short Feature Report write ({sent}/{len(tx)})")
            if self.clock() - started > self.timeout:
                raise TransportTimeout(f"Feature Report send exceeded {self.timeout:.3f}s")
            response = self.handle.get_feature_report(REPORT_ID, REPORT_LENGTH + 1)
        except PermissionError as exc:
            self._log(request, packet, None, started, "permission_denied")
            raise PermissionDenied(str(exc)) from exc
        except TimeoutError as exc:
            self._log(request, packet, None, started, "timeout")
            raise TransportTimeout(str(exc)) from exc
        except TransportTimeout as exc:
            self._log(request, packet, None, started, "timeout")
            raise
        except MalformedReport:
            self._log(request, packet, None, started, "malformed_request_or_write")
            raise
        except (OSError, IOError) as exc:
            self._log(request, packet, None, started, "transport_error")
            message = str(exc).lower()
            if "permission" in message or "access denied" in message:
                raise PermissionDenied(str(exc)) from exc
            if any(word in message for word in ("disconnect", "no such device", "not connected")):
                raise DeviceDisconnected(str(exc)) from exc
            raise TransportError(str(exc)) from exc
        if self.clock() - started > self.timeout:
            self._log(request, packet, bytes(response) if response else None, started, "timeout")
            raise TransportTimeout(f"Feature Report exchange exceeded {self.timeout:.3f}s")
        raw = bytes(response or b"")
        if len(raw) == REPORT_LENGTH + 1 and raw[0] == REPORT_ID:
            payload = raw[1:]
        elif len(raw) == REPORT_LENGTH:
            payload = raw
        else:
            self._log(request, packet, raw, started, "short_response")
            raise MalformedReport(f"expected 64-byte response (with optional report ID), got {len(raw)} bytes")
        try:
            decoded = request.decode(payload)
        except MalformedReport:
            self._log(request, packet, raw, started, "malformed_response")
            raise
        self._log(request, packet, raw, started, "ok")
        return decoded

    def _log(self, request: Query, packet: bytes, response: bytes | None, started: float, outcome: str):
        record = ExchangeRecord("feature_exchange", request.opcode, REPORT_ID, REPORT_LENGTH,
                                round((self.clock() - started) * 1000, 3), packet.hex(),
                                response.hex() if response else None, outcome)
        self.last_exchange = record
        logger.info("HID feature exchange", extra={"hid_event": asdict(record)})


class K86Client:
    def __init__(self, backend: Any | None = None, selector: DeviceSelector = DeviceSelector(), timeout: float = 1.0):
        self.backend = backend or HidApiBackend()
        self.selector = selector
        self.timeout = timeout

    def discover(self) -> list[DeviceInfo]:
        return discover_devices(self.backend)

    def open(self, selected: DeviceInfo | None = None) -> HidConnection:
        if self.selector != DeviceSelector():
            raise IncorrectDevice("this client supports only the validated ATTACK SHARK K86 selector")
        devices = self.discover()
        if selected is None:
            device = select_device(devices, self.selector)
        else:
            # Do not let callers bypass current hidapi enumeration by passing a
            # fabricated or stale DeviceInfo/path. Resolve only an exact row
            # returned by this connection attempt.
            current_matches = [candidate for candidate in devices if candidate == selected]
            if not current_matches:
                raise IncorrectDevice("selected device was not returned by current HID enumeration")
            if len(current_matches) != 1:
                raise IncorrectDevice("selected device is ambiguous in current HID enumeration")
            device = current_matches[0]
        if not self.selector.matches(device):
            raise IncorrectDevice("selected device does not match the required VID:PID, interface, and usage")
        try:
            handle = self.backend.open_path(device.path)
        except (PermissionDenied, DeviceDisconnected, DeviceOpenError):
            raise
        except PermissionError as exc:
            raise PermissionDenied(str(exc)) from exc
        except OSError as exc:
            raise _classify_open_error(device.path, exc) from exc
        try:
            validate_descriptor(_descriptor_from_handle(handle, device.path, device), device)
        except Exception:
            handle.close()
            raise
        return HidConnection(handle, device, timeout=self.timeout)

    def identify(self) -> int:
        from .protocol import identify_query, parse_device_id
        with self.open() as connection:
            response = connection.feature_roundtrip(identify_query())
            device_id = parse_device_id(response)
            self.last_exchange = connection.last_exchange
            return device_id

    def read_yc500(self, request: Query, *, allow_hardware: bool = False):
        """Perform one explicitly authorized yc500 GET after same-session identification."""
        if not allow_hardware:
            raise UnauthorizedWrite("physical query requires allow_hardware=True")
        if request.family != "yc500" or request.opcode not in READ_OPCODES or request.opcode == 0x8F:
            raise UnauthorizedWrite("request is not a supported yc500 configuration GET")
        with self.open() as connection:
            device_id = parse_device_id(connection.feature_roundtrip(identify_query()))
            if device_id != EXPECTED_DEVICE_ID:
                raise IncorrectDevice(f"yc500 query refused for internal device ID {device_id}")
            raw = connection.feature_roundtrip(request, allow_configuration=True)
            self.last_exchange = connection.last_exchange
            return decode_yc500_response(request, raw)
