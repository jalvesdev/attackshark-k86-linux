"""HID enumeration and fail-closed selection."""
from dataclasses import dataclass
from typing import Any, Iterable

from .errors import (AmbiguousDevice, DeviceNotFound, IncorrectDevice,
                     IncorrectInterface, PermissionDenied, TransportError)

VENDOR_ID = 0x3151
PRODUCT_ID = 0x4015
INTERFACE_NUMBER = 2
VENDOR_USAGE_PAGE = 0xFFFF
VENDOR_USAGE = 0x02


@dataclass(frozen=True)
class DeviceInfo:
    path: Any
    vendor_id: int
    product_id: int
    interface_number: int
    usage_page: int
    usage: int
    product_string: str = ""
    manufacturer_string: str = ""
    bus_type: int | None = None

    @classmethod
    def from_mapping(cls, row: dict[str, Any]) -> "DeviceInfo":
        path = row.get("path")
        if path is None:
            raise ValueError("hidapi entry has no path")
        return cls(
            path=path,
            vendor_id=int(row.get("vendor_id", 0)),
            product_id=int(row.get("product_id", 0)),
            interface_number=int(row.get("interface_number", -1)),
            usage_page=int(row.get("usage_page", 0)),
            usage=int(row.get("usage", 0)),
            product_string=row.get("product_string") or "",
            manufacturer_string=row.get("manufacturer_string") or "",
            bus_type=int(row["bus_type"]) if row.get("bus_type") is not None else None,
        )


@dataclass(frozen=True)
class DeviceSelector:
    vendor_id: int = VENDOR_ID
    product_id: int = PRODUCT_ID
    interface_number: int = INTERFACE_NUMBER
    usage_page: int = VENDOR_USAGE_PAGE
    usage: int = VENDOR_USAGE

    def matches(self, device: DeviceInfo) -> bool:
        reported_usage = (device.usage_page, device.usage)
        usage_is_missing = reported_usage == (0, 0)
        return (
            device.vendor_id == self.vendor_id
            and device.product_id == self.product_id
            and device.interface_number == self.interface_number
            and (usage_is_missing or reported_usage == (self.usage_page, self.usage))
            and device.bus_type == 1  # HID_API_BUS_USB; fail closed if unavailable
        )


def discover_devices(backend: Any) -> list[DeviceInfo]:
    """Enumerate HID nodes and retain the expected vendor collection only."""
    try:
        rows = backend.enumerate(VENDOR_ID, PRODUCT_ID)
    except PermissionError as exc:
        raise PermissionDenied(f"HID enumeration permission denied: {exc}") from exc
    except OSError as exc:
        raise TransportError(f"HID enumeration failed: {exc}") from exc
    return [DeviceInfo.from_mapping(row) for row in rows]


def select_device(devices: Iterable[DeviceInfo], selector: DeviceSelector = DeviceSelector()) -> DeviceInfo:
    candidates = list(devices)
    if any(d.vendor_id != selector.vendor_id or d.product_id != selector.product_id for d in candidates):
        # Enumeration can be broader than the requested pair; don't select these rows.
        candidates = [d for d in candidates if (d.vendor_id, d.product_id) == (selector.vendor_id, selector.product_id)]
    matching_pair = [d for d in candidates if (d.vendor_id, d.product_id) == (selector.vendor_id, selector.product_id)]
    if not matching_pair:
        raise DeviceNotFound(f"USB device {selector.vendor_id:04X}:{selector.product_id:04X} not found")
    # Select the required interface number before validating its collection.
    # Composite keyboards expose several HID interfaces for the same VID:PID;
    # their presence must not make an otherwise valid target look incorrect.
    interface_candidates = [d for d in matching_pair if d.interface_number == selector.interface_number]
    if not interface_candidates:
        found = sorted({d.interface_number for d in matching_pair})
        raise IncorrectInterface(f"expected HID interface {selector.interface_number}; found {found}")
    matches = [d for d in interface_candidates if selector.matches(d)]
    if not matches:
        raise IncorrectDevice(
            f"interface {selector.interface_number} on matching VID:PID lacks the expected USB "
            f"vendor usage descriptor {selector.usage_page:04X}:{selector.usage:04X} or USB bus metadata"
        )
    if len(matches) != 1:
        raise AmbiguousDevice(f"multiple matching HID collections ({len(matches)})")
    # A (0, 0) usage pair is an incomplete hidapi record, not proof that the
    # collection is compatible. K86Client.open() must validate the descriptor
    # for that exact enumerated path before returning a usable connection.
    return matches[0]
