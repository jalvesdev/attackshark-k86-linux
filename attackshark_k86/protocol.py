"""Protocol facts and codecs. This module performs no I/O."""
from dataclasses import dataclass
from enum import Enum
from typing import Callable

from .errors import IncorrectDevice, MalformedReport, UnauthorizedWrite

REPORT_ID = 0
REPORT_LENGTH = 64
IDENTIFY_OPCODE = 0x8F
EXPECTED_DEVICE_ID = 1168


class Checksum(Enum):
    NONE = "none"
    BIT7 = "bit7"
    BIT8 = "bit8"


def checksum_value(data: bytes | bytearray, covered: int) -> int:
    return (0xFF - (sum(data[:covered]) & 0xFF)) & 0xFF


def checksum_valid(report: bytes, mode: Checksum) -> bool:
    if len(report) != REPORT_LENGTH:
        return False
    if mode is Checksum.NONE:
        return True
    index, covered = (7, 7) if mode is Checksum.BIT7 else (8, 8)
    return report[index] == checksum_value(report, covered)


@dataclass(frozen=True)
class Query:
    name: str
    opcode: int
    payload: bytes = b""
    checksum: Checksum = Checksum.BIT7
    response_kind: str = "echo"
    family: str = "yc500"

    def encode(self) -> bytes:
        if self.family != "yc500":
            raise UnauthorizedWrite("only yc500 query codecs are supported")
        if self.opcode not in READ_OPCODES:
            raise UnauthorizedWrite(f"opcode 0x{self.opcode:02X} is not an allowed read command")
        if len(self.payload) > 55:
            raise ValueError("query payload exceeds bytes 1..55")
        report = bytearray(REPORT_LENGTH)
        report[0] = self.opcode
        report[1:1 + len(self.payload)] = self.payload
        if self.checksum is Checksum.BIT7:
            report[7] = checksum_value(report, 7)
        elif self.checksum is Checksum.BIT8:
            report[8] = checksum_value(report, 8)
        return bytes(report)

    def decode(self, report: bytes) -> bytes:
        if len(report) != REPORT_LENGTH:
            raise MalformedReport(f"expected 64-byte response, received {len(report)}")
        if self.response_kind == "echo" and report[0] != self.opcode:
            raise MalformedReport(f"expected response opcode 0x{self.opcode:02X}, got 0x{report[0]:02X}")
        return report


READ_OPCODES = frozenset({0x80, 0x85, 0x86, 0x87, 0x88, 0x89, 0x8B, 0x8C, 0x8F, 0x90, 0x91, 0x92, 0x97})


def query(opcode: int, name: str, payload: bytes = b"", response_kind: str = "echo", checksum: Checksum = Checksum.BIT7, family: str = "yc500") -> Query:
    return Query(name=name, opcode=opcode, payload=payload, checksum=checksum, response_kind=response_kind, family=family)


def identify_query() -> Query:
    return query(IDENTIFY_OPCODE, "identify")


def parse_device_id(report: bytes) -> int:
    identify_query().decode(report)
    device_id = int.from_bytes(report[1:5], "little")
    if device_id == 0 or device_id == 0xFFFFFFFF:
        raise MalformedReport(f"invalid device ID 0x{device_id:08X}")
    return device_id


def decode_yc500_response(request: Query, report: bytes):
    """Decode documented yc500 GET replies. Response checksum rules are not documented."""
    if request.family != "yc500" or request.opcode not in READ_OPCODES:
        raise UnauthorizedWrite("query is not an allowed yc500 GET")
    raw = request.decode(report)
    op = request.opcode
    if op == 0x8F:
        return parse_device_id(raw)
    if op == 0x80:
        return (raw[2] << 8) | raw[1]
    if op == 0x85:
        return raw[1]  # Active profile, zero based; no profile selector payload.
    if op == 0x86:
        return {"flags": raw[2], "fn_matrix": raw[3], "power_save": raw[4]}
    if op in (0x87, 0x88):
        return {"mode": raw[1], "speed": raw[2], "brightness": raw[3],
                "option_flags": raw[4], "rgb": tuple(raw[5:8])}
    if op in (0x89, 0x8B, 0x90):
        return raw  # Documented as a raw 64-byte page.
    if op == 0x8C:
        return raw  # sharkfin notes this readback is stable but may not reflect writes.
    if op == 0x91:
        if not 1 <= raw[2] <= 10:
            raise MalformedReport(f"yc500 debounce value outside documented range 1..10: {raw[2]}")
        return raw[2]
    if op == 0x92:
        return tuple(int.from_bytes(raw[i:i + 2], "little") for i in range(1, 9, 2))
    if op == 0x97:
        if raw[1] not in (0, 1):
            raise MalformedReport(f"unexpected yc500 auto-OS value {raw[1]}")
        return raw[1] == 1
    raise MalformedReport(f"no yc500 response decoder for opcode 0x{op:02X}")


def yc500_queries() -> dict[str, Callable[..., Query]]:
    """Safe GET codecs documented for yc500; no operation is sent here."""
    return {
        "identify": identify_query,
        "revision": lambda: query(0x80, "revision"),
        "profile": lambda: query(0x85, "profile"),
        "options": lambda: query(0x86, "options"),
        "led_params": lambda: query(0x87, "led_params"),
        "side_led_params": lambda: query(0x88, "side_led_params"),
        "keymap_page": lambda profile, page: _page_query(0x89, "keymap_page", profile, page, 7),
        "macro_page": lambda slot, page: _macro_query(slot, page),
        "userpic": lambda: query(0x8C, "userpic"),
        "fn_page": lambda profile, page: _page_query(0x90, "fn_page", profile, page, 7),
        "debounce": lambda: query(0x91, "debounce"),
        "sleep_timers": lambda: query(0x92, "sleep_timers"),
        "auto_os": lambda: query(0x97, "auto_os"),
    }


def _page_query(opcode: int, name: str, first: int, page: int, max_page: int) -> Query:
    if not (0 <= first <= 0xFF and 0 <= page <= max_page):
        raise ValueError(f"profile and page must be bytes; page must be 0..{max_page}")
    return query(opcode, name, bytes((first, page)), response_kind="raw")


def _macro_query(slot: int, page: int) -> Query:
    if not (0 <= slot < 50 and 0 <= page <= 3):
        raise ValueError("macro slot must be 0..49 and page must be 0..3")
    return query(0x8B, "macro_page", bytes((slot, page)), response_kind="raw")


def parse_report_descriptor(descriptor: bytes) -> dict[str, int | bool]:
    """Extract top-level collection usage and report-ID-0 feature bit length."""
    globals_: dict[str, int] = {"usage_page": 0, "report_size": 0, "report_count": 0, "report_id": 0}
    stack: list[dict[str, int]] = []
    local_usages: list[int] = []
    top_page = top_usage = None
    collection_depth = 0
    feature_bits: dict[int, int] = {}
    i = 0
    while i < len(descriptor):
        prefix = descriptor[i]
        i += 1
        if prefix == 0xFE:
            if i + 2 > len(descriptor):
                raise MalformedReport("truncated HID long item")
            size = descriptor[i]
            i += 2  # size + long-item tag
            i += size
            if i > len(descriptor):
                raise MalformedReport("truncated HID long-item data")
            continue
        size_code = prefix & 0x03
        size = 4 if size_code == 3 else size_code
        if i + size > len(descriptor):
            raise MalformedReport("truncated HID short item")
        raw = descriptor[i:i + size]
        i += size
        value = int.from_bytes(raw, "little", signed=False) if raw else 0
        item_type = (prefix >> 2) & 0x03
        tag = (prefix >> 4) & 0x0F
        if item_type == 1:  # global
            if tag == 0:
                globals_["usage_page"] = value
            elif tag == 7:
                globals_["report_size"] = value
            elif tag == 8:
                globals_["report_id"] = value
            elif tag == 9:
                globals_["report_count"] = value
            elif tag == 10:
                stack.append(globals_.copy())
            elif tag == 11:
                if not stack:
                    raise MalformedReport("HID global Pop without Push")
                globals_ = stack.pop()
        elif item_type == 2:  # local Usage
            if tag == 0:
                local_usages.append(value & 0xFFFF)
        elif item_type == 0:  # main
            if tag == 10:  # Collection
                if collection_depth == 0:
                    top_page = globals_["usage_page"]
                    top_usage = local_usages[0] if local_usages else None
                collection_depth += 1
            elif tag == 12:  # End Collection
                collection_depth = max(0, collection_depth - 1)
            elif tag == 11:  # Feature
                bits = globals_["report_size"] * globals_["report_count"]
                rid = globals_["report_id"]
                feature_bits[rid] = feature_bits.get(rid, 0) + bits
            local_usages.clear()
    if stack:
        raise MalformedReport("unbalanced HID global Push/Pop")
    return {"usage_page": top_page or 0, "usage": top_usage or 0,
            "report_id_0_feature_bytes": feature_bits.get(0, 0) // 8,
            "has_report_id_0_feature_64": feature_bits.get(0, 0) == 64 * 8}
