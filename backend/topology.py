"""Build a LAN tree: WAN → core → ports → 子路由 / 终端."""

from __future__ import annotations

import ipaddress
from typing import Any

from talkers import as_int, parse_ip

AP_HINTS = ("易展", "mesh", "xdr", "eap", "deco", "ap-", "wifi6", "wifi 6")
ROUTER_HINTS = AP_HINTS + ("router", "openwrt", "asus", "tplink", "tp-link", "tp_link", "redmi")


def _truthy(value: Any) -> bool:
    return str(value).lower() == "true"


def _mac(value: Any) -> str | None:
    if not value:
        return None
    text = str(value).strip().upper().replace("-", ":")
    if len(text) < 11:
        return None
    return text


def short_name(host_name: str, comment: str) -> str:
    host = (host_name or "").strip()
    note = (comment or "").strip()
    if host and any(token in host.lower() or token in host for token in ("xdr", "易展", "mesh", "deco", "eap")):
        label = host
    else:
        label = note or host
    if not label:
        return ""
    lowered = label.lower()
    if "aircondition" in lowered or "zhimi" in lowered:
        return "空调 " + label[-4:]
    if "dmaker" in lowered or ( "fan" in lowered and "fan" in host.lower()):
        return "风扇"
    if "soundbox" in lowered or "lx06" in lowered:
        return "小爱音箱"
    label = label.replace("易展版", "").replace("TL-", "")
    return label[:18]


def _haystack(name: str, comment: str) -> str:
    return f"{name} {comment}".lower()


def is_access_point(name: str, comment: str) -> bool:
    text = _haystack(name, comment)
    return any(hint in text for hint in AP_HINTS)


def is_subrouter(
    name: str,
    comment: str,
    neighbor: bool,
    extra_nets: list[str],
) -> bool:
    if neighbor:
        return True
    if extra_nets:
        return True
    text = _haystack(name, comment)
    return any(hint in text for hint in ROUTER_HINTS)


def _extra_nets(allowed: str) -> list[str]:
    nets: list[str] = []
    for part in (allowed or "").split(","):
        part = part.strip()
        if not part:
            continue
        try:
            net = ipaddress.ip_network(part, strict=False)
        except ValueError:
            continue
        if net.prefixlen < 32:
            nets.append(str(net))
    return nets


def _talker_map(talkers: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    out: dict[str, dict[str, int]] = {}
    for row in talkers:
        ip = row.get("ip")
        if ip:
            out[ip] = {
                "down_bps": as_int(row.get("down_bps")),
                "up_bps": as_int(row.get("up_bps")),
            }
    return out


def _node(
    *,
    id: str,
    kind: str,
    label: str,
    sub: str = "",
    ip: str | None = None,
    mac: str | None = None,
    down_bps: int = 0,
    up_bps: int = 0,
    online: bool = True,
    children: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "id": id,
        "kind": kind,
        "label": label,
        "sub": sub,
        "ip": ip,
        "mac": mac,
        "down_bps": down_bps,
        "up_bps": up_bps,
        "online": online,
        "children": children or [],
    }


def build_topology(
    *,
    identity: str,
    board: str,
    lan_ip: str,
    wan: dict[str, Any],
    leases: list[dict[str, Any]],
    arp: list[dict[str, Any]],
    neighbors: list[dict[str, Any]],
    bridge_hosts: list[dict[str, Any]],
    bridge_ports: list[dict[str, Any]],
    wg_peers: list[dict[str, Any]],
    talkers: list[dict[str, Any]],
    iface_rates: dict[str, dict[str, int]],
) -> dict[str, Any]:
    rates = _talker_map(talkers)
    by_mac: dict[str, dict[str, Any]] = {}

    def upsert(mac: str | None, **fields: Any) -> None:
        if not mac:
            return
        row = by_mac.setdefault(mac, {"mac": mac})
        for key, value in fields.items():
            if value not in (None, ""):
                row[key] = value

    for lease in leases:
        mac = _mac(lease.get("active-mac-address") or lease.get("mac-address"))
        upsert(
            mac,
            ip=parse_ip(lease.get("active-address") or lease.get("address")),
            host_name=lease.get("host-name") or "",
            comment=lease.get("comment") or "",
            lease_status=lease.get("status") or "",
        )
    for row in arp:
        if (row.get("status") or "") == "failed":
            continue
        mac = _mac(row.get("mac-address"))
        upsert(mac, ip=parse_ip(row.get("address")), arp_iface=row.get("interface") or "")

    neighbor_macs: set[str] = set()
    neighbor_names: dict[str, str] = {}
    for nb in neighbors:
        addr = parse_ip(nb.get("address") or nb.get("address4"))
        if addr == lan_ip:
            continue
        if (nb.get("identity") or "") == identity and addr in (None, lan_ip):
            continue
        mac = _mac(nb.get("mac-address"))
        if not mac:
            continue
        neighbor_macs.add(mac)
        neighbor_names[mac] = nb.get("identity") or addr or mac
        upsert(mac, ip=addr, host_name=nb.get("identity") or "", neighbor=True)

    port_of: dict[str, str] = {}
    for host in bridge_hosts:
        if _truthy(host.get("local")):
            continue
        mac = _mac(host.get("mac-address"))
        port = host.get("on-interface") or host.get("interface")
        if mac and port:
            port_of[mac] = port
            upsert(mac, port=port)

    active_ports: list[str] = []
    for port in bridge_ports:
        name = port.get("interface")
        if not name:
            continue
        if _truthy(port.get("inactive")):
            continue
        active_ports.append(name)

    grouped: dict[str, list[str]] = {name: [] for name in active_ports}
    for mac, port in port_of.items():
        grouped.setdefault(port, []).append(mac)

    port_nodes: list[dict[str, Any]] = []
    for port in sorted(grouped.keys(), key=lambda n: (n not in active_ports, n)):
        macs = grouped[port]
        if not macs and port not in active_ports:
            continue
        hosts: list[dict[str, Any]] = []
        routers: list[dict[str, Any]] = []
        for mac in sorted(macs):
            info = by_mac.get(mac, {"mac": mac})
            ip = info.get("ip")
            name = short_name(info.get("host_name") or "", info.get("comment") or "") or ip or mac[-8:]
            traffic = rates.get(ip or "", {})
            node = _node(
                id=f"mac:{mac}",
                kind="host",
                label=name,
                sub=ip or mac,
                ip=ip,
                mac=mac,
                down_bps=traffic.get("down_bps", 0),
                up_bps=traffic.get("up_bps", 0),
                online=info.get("lease_status", "bound") != "waiting",
            )
            if is_subrouter(
                info.get("host_name") or "",
                info.get("comment") or "",
                mac in neighbor_macs,
                [],
            ):
                node["kind"] = "router"
                if mac in neighbor_names:
                    node["label"] = neighbor_names[mac]
                node["ap"] = is_access_point(info.get("host_name") or "", info.get("comment") or "")
                routers.append(node)
            else:
                hosts.append(node)

        children: list[dict[str, Any]]
        aps = [r for r in routers if r.get("ap")]
        if len(aps) == 1 and len(routers) == 1:
            aps[0]["children"] = hosts
            children = aps
        else:
            children = routers + hosts

        rate = iface_rates.get(port, {})
        port_nodes.append(
            _node(
                id=f"port:{port}",
                kind="port",
                label=port,
                sub=f"{len(children)} 台",
                down_bps=as_int(rate.get("rx_bps")),
                up_bps=as_int(rate.get("tx_bps")),
                children=children,
            )
        )

    wg_children: list[dict[str, Any]] = []
    for peer in wg_peers:
        if _truthy(peer.get("disabled")):
            continue
        allowed = peer.get("allowed-address") or ""
        nets = _extra_nets(allowed)
        ip = None
        for part in allowed.split(","):
            try:
                iface = ipaddress.ip_interface(part.strip())
            except ValueError:
                continue
            if iface.network.prefixlen >= 32:
                ip = str(iface.ip)
                break
        label = (peer.get("comment") or peer.get("name") or "peer").strip()
        handshake = peer.get("last-handshake") or ""
        online = bool(handshake) and not str(handshake).startswith("18h")
        # 有握手且不是天级过期：粗略在线。精确点：有 current-endpoint 即在线。
        online = bool(peer.get("current-endpoint-address"))
        node = _node(
            id=f"wg:{peer.get('name')}",
            kind="router" if nets else "peer",
            label=label,
            sub=ip or allowed,
            ip=ip,
            down_bps=as_int(peer.get("rx")),  # cumulative; display as 累计 separately
            up_bps=as_int(peer.get("tx")),
            online=online,
            children=[
                _node(id=f"net:{net}", kind="net", label=net, sub="远端网段")
                for net in nets
            ],
        )
        # WG rx/tx 是累计字节，不当成 bps
        node["down_bps"] = 0
        node["up_bps"] = 0
        node["bytes_rx"] = as_int(peer.get("rx"))
        node["bytes_tx"] = as_int(peer.get("tx"))
        wg_children.append(node)

    if wg_children:
        wg_rate = iface_rates.get("wireguard1", {})
        port_nodes.append(
            _node(
                id="port:wireguard1",
                kind="port",
                label="wireguard1",
                sub=f"{len(wg_children)} 端",
                down_bps=as_int(wg_rate.get("rx_bps")),
                up_bps=as_int(wg_rate.get("tx_bps")),
                children=wg_children,
            )
        )

    core = _node(
        id="core",
        kind="core",
        label=identity or "MikroTik",
        sub=f"{lan_ip} · {board}".strip(" ·"),
        ip=lan_ip,
        children=port_nodes,
    )
    return _node(
        id="internet",
        kind="cloud",
        label="公网",
        sub=wan.get("address") or wan.get("name") or "",
        down_bps=as_int(wan.get("rx_bps")),
        up_bps=as_int(wan.get("tx_bps")),
        children=[core],
    )
