"""Read-only HID library for the ATTACK SHARK K86 (yc500 candidate)."""

from .device import DeviceInfo, DeviceSelector, discover_devices, select_device
from .protocol import identify_query, parse_device_id

__all__ = ["DeviceInfo", "DeviceSelector", "discover_devices", "select_device", "identify_query", "parse_device_id"]
__version__ = "0.1.0"
