"""Interface board: type buckets, RJ45 ports, address join."""

from __future__ import annotations

from typing import Any

TYPE_BUCKETS = (
    ("ether", "ETHER"),
    ("wifi", "WIFI"),
    ("bridge", "BRIDGE"),
    ("wg", "WG"),
    ("pppoe-out", "PPPOE"),
    ("loopback", "LOOPBACK"),
    ("zerotier", "ZT"),
)

_WIFI_TYPES = {"wifi", "wlan"}
_TYPE_RANK = {
    "ether": 0,
    "pppoe-out": 1,
    "wifi": 2,
    "wlan": 2,
    "bridge": 3,
    "wg": 4,
    "zerotier": 5,
    "loopback": 6,
}


def _bucket_key(iface_type: str) -> str:
    if iface_type in _WIFI_TYPES:
        return "wifi"
    return iface_type or "other"


def type_counts(ifaces: list[dict[str, Any]]) -> list[dict[str, Any]]:
    tally: dict[str, int] = {}
    for row in ifaces:
        key = _bucket_key(row.get("type") or "")
        tally[key] = tally.get(key, 0) + 1
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for key, label in TYPE_BUCKETS:
        if tally.get(key):
            out.append({"key": key, "label": label, "count": tally[key]})
            seen.add(key)
    for key, count in sorted(tally.items()):
        if key not in seen:
            out.append({"key": key, "label": key.upper(), "count": count})
    return out


def physical_ports(ifaces: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ports = [row for row in ifaces if row.get("type") == "ether"]

    def sort_key(row: dict[str, Any]) -> tuple[int, str]:
        name = row.get("name") or ""
        if name.lower() in {"wan", "ether1"} or name.lower().startswith("wan"):
            return (0, name)
        return (1, name)

    return sorted(ports, key=sort_key)


def attach_addresses(
    ifaces: list[dict[str, Any]],
    addresses: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    by_iface: dict[str, list[str]] = {}
    for addr in addresses:
        name = addr.get("actual-interface") or addr.get("interface")
        value = addr.get("address")
        if name and value:
            by_iface.setdefault(name, []).append(value)
    out = []
    for row in ifaces:
        item = dict(row)
        item["addresses"] = list(by_iface.get(row.get("name") or "", []))
        out.append(item)
    return out


def sort_interface_cards(ifaces: list[dict[str, Any]]) -> list[dict[str, Any]]:
    def key(row: dict[str, Any]) -> tuple[int, int, int, int, str]:
        name = row.get("name") or ""
        disabled = 2 if row.get("disabled") else 0
        down = 0 if row.get("running") else 1
        uplink = 0 if name in {"wan", "ether1", "pppoe-out1"} else 1
        rank = _TYPE_RANK.get(row.get("type") or "", 9)
        return (disabled, down, uplink, rank, name)

    return sorted(ifaces, key=key)
