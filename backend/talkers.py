"""LAN Top Talker aggregation from RouterOS connection tracking."""

from __future__ import annotations

import ipaddress
from collections import defaultdict
from typing import Any, Iterable


def parse_ip(value: str | None) -> str | None:
    if not value:
        return None
    text = value.split("%", 1)[0].strip()
    if not text:
        return None
    try:
        return str(ipaddress.ip_address(text))
    except ValueError:
        return None


def as_int(value: Any, default: int = 0) -> int:
    if value is None or value == "":
        return default
    try:
        return int(str(value).split(".", 1)[0])
    except (TypeError, ValueError):
        return default


def is_lan(ip: str | None, networks: list[ipaddress._BaseNetwork]) -> bool:
    if not ip:
        return False
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return any(addr in net for net in networks)


def parse_networks(cidrs: Iterable[str]) -> list[ipaddress._BaseNetwork]:
    return [ipaddress.ip_network(item, strict=False) for item in cidrs]


def host_and_direction(
    conn: dict[str, Any], networks: list[ipaddress._BaseNetwork]
) -> tuple[str | None, int, int, str | None, int, int]:
    """Return (lan_host, down_bps, up_bps, peer_ip, down_bytes, up_bytes)."""
    src = parse_ip(conn.get("src-address"))
    dst = parse_ip(conn.get("dst-address"))
    reply_src = parse_ip(conn.get("reply-src-address"))
    orig = as_int(conn.get("orig-rate"))
    repl = as_int(conn.get("repl-rate"))
    orig_b = as_int(conn.get("orig-bytes"))
    repl_b = as_int(conn.get("repl-bytes"))

    if is_lan(src, networks):
        return src, repl, orig, dst, repl_b, orig_b
    if is_lan(reply_src, networks):
        return reply_src, orig, repl, src, orig_b, repl_b
    if is_lan(dst, networks):
        return dst, orig, repl, src, orig_b, repl_b
    return None, 0, 0, None, 0, 0


def aggregate_talkers(
    connections: Iterable[dict[str, Any]],
    lan_cidrs: Iterable[str],
    names: dict[str, str] | None = None,
    exclude: Iterable[str] = (),
    limit: int | None = 20,
) -> list[dict[str, Any]]:
    networks = parse_networks(lan_cidrs)
    skip = {parse_ip(ip) for ip in exclude}
    skip.discard(None)
    names = names or {}

    hosts: dict[str, dict[str, Any]] = {}
    for conn in connections:
        host, down, up, peer, down_b, up_b = host_and_direction(conn, networks)
        if not host or host in skip:
            continue
        row = hosts.get(host)
        if row is None:
            row = {
                "ip": host,
                "name": names.get(host) or host,
                "down_bps": 0,
                "up_bps": 0,
                "down_bytes": 0,
                "up_bytes": 0,
                "conns": 0,
                "peers": defaultdict(lambda: {"down_bps": 0, "up_bps": 0, "conns": 0}),
            }
            hosts[host] = row
        row["down_bps"] += down
        row["up_bps"] += up
        row["down_bytes"] += down_b
        row["up_bytes"] += up_b
        row["conns"] += 1
        if peer:
            p = row["peers"][peer]
            p["down_bps"] += down
            p["up_bps"] += up
            p["conns"] += 1

    ranked = sorted(
        hosts.values(),
        key=lambda item: item["down_bps"] + item["up_bps"],
        reverse=True,
    )
    sliced = ranked if limit is None else ranked[:limit]
    out = []
    for item in sliced:
        peers = sorted(
            (
                {"ip": ip, **stats}
                for ip, stats in item["peers"].items()
            ),
            key=lambda p: p["down_bps"] + p["up_bps"],
            reverse=True,
        )[:5]
        out.append(
            {
                "ip": item["ip"],
                "name": item["name"],
                "down_bps": item["down_bps"],
                "up_bps": item["up_bps"],
                "down_bytes": item["down_bytes"],
                "up_bytes": item["up_bytes"],
                "conns": item["conns"],
                "peers": peers,
            }
        )
    return out


def remember_peaks(talkers: list[dict[str, Any]], store: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep per-host peak rates and retain idle hosts so the table does not reshuffle away."""
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for row in talkers:
        ip = row.get("ip")
        if not ip:
            continue
        seen.add(ip)
        prev = store.get(ip, {})
        total = int(row.get("down_bps") or 0) + int(row.get("up_bps") or 0)
        cur_down = int(row.get("down_bytes") or 0)
        cur_up = int(row.get("up_bytes") or 0)
        last_down = int(prev.get("last_down_bytes") or 0)
        last_up = int(prev.get("last_up_bytes") or 0)
        acc_down = int(prev.get("acc_down_bytes") or 0)
        acc_up = int(prev.get("acc_up_bytes") or 0)
        if cur_down >= last_down:
            acc_down += cur_down - last_down
        last_down = cur_down
        if cur_up >= last_up:
            acc_up += cur_up - last_up
        last_up = cur_up
        merged = {
            **row,
            "peak_down_bps": max(int(prev.get("peak_down_bps") or 0), int(row.get("down_bps") or 0)),
            "peak_up_bps": max(int(prev.get("peak_up_bps") or 0), int(row.get("up_bps") or 0)),
            "peak_total_bps": max(int(prev.get("peak_total_bps") or 0), total),
            "acc_down_bytes": acc_down,
            "acc_up_bytes": acc_up,
            "last_down_bytes": last_down,
            "last_up_bytes": last_up,
        }
        store[ip] = merged
        out.append(merged)
    for ip, prev in store.items():
        if ip in seen:
            continue
        out.append(
            {
                **prev,
                "down_bps": 0,
                "up_bps": 0,
                "down_bytes": 0,
                "up_bytes": 0,
                "conns": 0,
                "peers": [],
            }
        )
    return out
