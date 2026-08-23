from __future__ import annotations

import asyncio
import ipaddress
import time
from collections import deque
from typing import Any

from rates import snapshot_rates
from ros import RouterOS
from store import SampleStore
from ifaces import attach_addresses, physical_ports, sort_interface_cards, type_counts
from talkers import aggregate_talkers, as_int, parse_ip, remember_peaks
from topology import build_topology

HIDDEN_TYPES = {"loopback"}
HISTORY_POINTS = 360


def _truthy(value: Any) -> bool:
    return str(value).lower() == "true"


def detect_wan(addresses: list[dict[str, Any]], interfaces: list[dict[str, Any]]) -> str:
    for addr in addresses:
        ip = (addr.get("address") or "").split("/", 1)[0]
        iface = addr.get("actual-interface") or addr.get("interface")
        if not ip or not iface:
            continue
        try:
            parsed = ipaddress.ip_address(ip)
        except ValueError:
            continue
        if parsed.is_global:
            return iface
    for name in ("pppoe-out1", "wan", "ether1"):
        if any(i.get("name") == name and _truthy(i.get("running")) for i in interfaces):
            return name
    running = [i["name"] for i in interfaces if _truthy(i.get("running")) and i.get("type") != "loopback"]
    return running[0] if running else "pppoe-out1"


def lan_cidrs_and_router_ips(addresses: list[dict[str, Any]]) -> tuple[list[str], list[str]]:
    cidrs: list[str] = []
    routers: list[str] = []
    for addr in addresses:
        raw = addr.get("address") or ""
        try:
            iface_addr = ipaddress.ip_interface(raw)
        except ValueError:
            continue
        if iface_addr.ip.is_private and not iface_addr.ip.is_loopback:
            cidrs.append(str(iface_addr.network))
            routers.append(str(iface_addr.ip))
    return cidrs or ["10.1.1.0/24"], routers


def dhcp_names(leases: list[dict[str, Any]]) -> dict[str, str]:
    names: dict[str, str] = {}
    for lease in leases:
        ip = parse_ip(lease.get("address"))
        if not ip:
            continue
        label = (lease.get("comment") or "").strip() or (lease.get("host-name") or "").strip()
        if label:
            names[ip] = label
    return names


def public_address(addresses: list[dict[str, Any]], wan: str) -> str | None:
    for addr in addresses:
        iface = addr.get("actual-interface") or addr.get("interface")
        if iface != wan:
            continue
        ip = (addr.get("address") or "").split("/", 1)[0]
        return ip
    return None


class Poller:
    def __init__(self, ros: RouterOS, store: SampleStore, wan_hint: str | None = None) -> None:
        self.ros = ros
        self.store = store
        self.wan_hint = wan_hint
        self.snapshot: dict[str, Any] = {"ok": False, "error": "尚未采样"}
        self._prev: dict[str, dict[str, Any]] | None = None
        self._ring: deque[dict[str, Any]] = deque(maxlen=HISTORY_POINTS)
        self._last_prune = 0.0
        self._last_conn = 0.0
        self._leases: list[dict[str, Any]] = []
        self._connections: list[dict[str, Any]] = []
        self._neighbors: list[dict[str, Any]] = []
        self._arp: list[dict[str, Any]] = []
        self._bridge_hosts: list[dict[str, Any]] = []
        self._bridge_ports: list[dict[str, Any]] = []
        self._wg_peers: list[dict[str, Any]] = []
        self._iface_rings: dict[str, deque] = {}
        self._talker_peaks: dict[str, dict[str, Any]] = {}
        self._lock = asyncio.Lock()
        self._task: asyncio.Task[None] | None = None

    def start(self) -> None:
        self._task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _loop(self) -> None:
        while True:
            started = time.time()
            try:
                async with self._lock:
                    await self._tick()
            except Exception as exc:  # noqa: BLE001 — keep last good snapshot
                self.snapshot = {**self.snapshot, "ok": False, "error": str(exc), "ts": time.time()}
            delay = max(0.2, 1.0 - (time.time() - started))
            await asyncio.sleep(delay)

    async def _tick(self) -> None:
        now = time.time()
        resource, identity, addresses, interfaces = await asyncio.gather(
            self.ros.get("/system/resource"),
            self.ros.get("/system/identity"),
            self.ros.get("/ip/address"),
            self.ros.get("/interface"),
        )
        if now - self._last_conn >= 2.0:
            (
                leases,
                connections,
                neighbors,
                arp,
                bridge_hosts,
                bridge_ports,
                wg_peers,
            ) = await asyncio.gather(
                self.ros.get_list("/ip/dhcp-server/lease"),
                self.ros.get_list("/ip/firewall/connection"),
                self.ros.get_list("/ip/neighbor"),
                self.ros.get_list("/ip/arp"),
                self.ros.get_list("/interface/bridge/host"),
                self.ros.get_list("/interface/bridge/port"),
                self.ros.get_list("/interface/wireguard/peers"),
            )
            self._leases = leases
            self._connections = connections
            self._neighbors = neighbors
            self._arp = arp
            self._bridge_hosts = bridge_hosts
            self._bridge_ports = bridge_ports
            self._wg_peers = wg_peers
            self._last_conn = now
        leases = self._leases
        connections = self._connections
        if isinstance(resource, list):
            resource = resource[0] if resource else {}
        if isinstance(identity, list):
            identity = identity[0] if identity else {}

        rates, self._prev = snapshot_rates(self._prev, interfaces, now)
        board = attach_addresses(rates, addresses if isinstance(addresses, list) else [])
        for row in board:
            ring = self._iface_rings.setdefault(row["name"], deque(maxlen=72))
            ring.append({"t": now, "rx": row["rx_bps"], "tx": row["tx_bps"]})
            row["spark"] = list(ring)
        board = sort_interface_cards(board)
        visible = [
            row
            for row in board
            if row["type"] not in HIDDEN_TYPES
            and not row["disabled"]
            and (row["running"] or row["rx_bps"] + row["tx_bps"] > 0)
        ]
        wan = self.wan_hint or detect_wan(addresses, interfaces)
        wan_row = next((r for r in visible if r["name"] == wan), visible[0] if visible else None)
        cidrs, routers = lan_cidrs_and_router_ips(addresses)
        talkers = remember_peaks(
            aggregate_talkers(
                connections,
                cidrs,
                names=dhcp_names(leases),
                exclude=routers,
                limit=64,
            ),
            self._talker_peaks,
        )
        lan_ip = routers[0] if routers else "10.1.1.1"
        iface_rates = {row["name"]: {"rx_bps": row["rx_bps"], "tx_bps": row["tx_bps"]} for row in visible}
        wan_info = {
            "name": wan,
            "address": public_address(addresses, wan),
            "rx_bps": wan_row["rx_bps"] if wan_row else 0,
            "tx_bps": wan_row["tx_bps"] if wan_row else 0,
        }
        topology = build_topology(
            identity=identity.get("name") or "MikroTik",
            board=resource.get("board-name") or "",
            lan_ip=lan_ip,
            wan=wan_info,
            leases=leases,
            arp=self._arp,
            neighbors=self._neighbors,
            bridge_hosts=self._bridge_hosts,
            bridge_ports=self._bridge_ports,
            wg_peers=self._wg_peers,
            talkers=talkers,
            iface_rates=iface_rates,
        )

        if wan_row:
            point = {"t": now, "rx": wan_row["rx_bps"], "tx": wan_row["tx_bps"]}
            self._ring.append(point)
            self.store.insert_many(now, board)
            if now - self._last_prune > 60:
                self.store.prune()
                self._last_prune = now

        total_mem = as_int(resource.get("total-memory"))
        free_mem = as_int(resource.get("free-memory"))
        mem_used = total_mem - free_mem if total_mem else 0

        self.snapshot = {
            "ok": True,
            "error": None,
            "ts": now,
            "identity": identity.get("name") or "MikroTik",
            "board": resource.get("board-name") or "",
            "version": resource.get("version") or "",
            "uptime": resource.get("uptime") or "",
            "cpu_load": as_int(resource.get("cpu-load")),
            "cpu_count": as_int(resource.get("cpu-count")),
            "mem_used": mem_used,
            "mem_total": total_mem,
            "wan": wan_info,
            "interfaces": board,
            "type_counts": type_counts(board),
            "physical_ports": physical_ports(board),
            "talkers": talkers,
            "topology": topology,
            "history": list(self._ring),
        }
