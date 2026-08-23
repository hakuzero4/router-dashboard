from topology import build_topology, is_subrouter, short_name


def _host(**kwargs):
    return kwargs


def test_xdr_hostname_is_subrouter():
    assert is_subrouter(
        name="TL-XDR3010易展版",
        comment="tp_link",
        neighbor=False,
        extra_nets=[],
    )
    assert not is_subrouter(name="iPhone", comment="", neighbor=False, extra_nets=[])


def test_neighbor_and_wg_lan_are_subrouters():
    assert is_subrouter(name="home", comment="", neighbor=True, extra_nets=[])
    assert is_subrouter(
        name="home",
        comment="home",
        neighbor=False,
        extra_nets=["10.23.0.0/16"],
    )


def test_short_name_strips_iot_noise():
    assert "空调" in short_name("zhimi-aircondition-ma4_mibt5595", "")
    assert short_name("naruto", "GTR7") == "GTR7"


def test_single_subrouter_on_port_nests_terminals():
    tree = build_topology(
        identity="hAP",
        board="hAP ax^2",
        lan_ip="10.1.1.1",
        wan={"name": "pppoe-out1", "address": "113.205.141.49", "rx_bps": 1000, "tx_bps": 200},
        leases=[
            {
                "address": "10.1.1.14",
                "mac-address": "6C:B1:58:0B:03:CD",
                "host-name": "TL-XDR3010易展版",
                "comment": "tp_link",
                "status": "bound",
            },
            {
                "address": "10.1.1.19",
                "mac-address": "F6:E3:52:C2:F4:AF",
                "host-name": "iPhone",
                "comment": "",
                "status": "bound",
            },
        ],
        arp=[],
        neighbors=[],
        bridge_hosts=[
            {"mac-address": "6C:B1:58:0B:03:CD", "on-interface": "ether5", "local": "false"},
            {"mac-address": "F6:E3:52:C2:F4:AF", "on-interface": "ether5", "local": "false"},
            {"mac-address": "48:AA:AA:AA:AA:AA", "on-interface": "ether5", "local": "true"},
        ],
        bridge_ports=[{"interface": "ether5", "inactive": "false"}],
        wg_peers=[],
        talkers=[{"ip": "10.1.1.19", "down_bps": 8000, "up_bps": 100}],
        iface_rates={"ether5": {"rx_bps": 9000, "tx_bps": 300}},
    )
    ports = tree["children"][0]["children"]
    ether5 = next(p for p in ports if p["label"] == "ether5")
    assert len(ether5["children"]) == 1
    ap = ether5["children"][0]
    assert ap["kind"] == "router"
    assert ap["ip"] == "10.1.1.14"
    assert "XDR3010" in ap["label"]
    assert [c["ip"] for c in ap["children"]] == ["10.1.1.19"]
    assert ap["children"][0]["down_bps"] == 8000


def test_mixed_port_keeps_pc_beside_neighbor_router():
    tree = build_topology(
        identity="hAP",
        board="ax2",
        lan_ip="10.1.1.1",
        wan={"name": "pppoe-out1", "address": "1.1.1.1", "rx_bps": 0, "tx_bps": 0},
        leases=[
            {
                "address": "10.1.1.10",
                "mac-address": "70:70:FC:02:C0:03",
                "host-name": "naruto",
                "comment": "GTR7",
                "status": "bound",
            }
        ],
        arp=[{"address": "10.1.1.3", "mac-address": "78:60:5B:3E:3C:54", "interface": "bridge1"}],
        neighbors=[
            {
                "identity": "home",
                "address": "10.1.1.3",
                "mac-address": "78:60:5B:3E:3C:54",
                "interface": "ether4,bridge1",
            }
        ],
        bridge_hosts=[
            {"mac-address": "70:70:FC:02:C0:03", "on-interface": "ether4", "local": "false"},
            {"mac-address": "78:60:5B:3E:3C:54", "on-interface": "ether4", "local": "false"},
        ],
        bridge_ports=[{"interface": "ether4", "inactive": "false"}],
        wg_peers=[
            {
                "name": "peer3",
                "comment": "home",
                "allowed-address": "10.0.1.2/32,10.23.0.0/16",
                "current-endpoint-address": "14.1.1.1",
                "last-handshake": "1m",
                "rx": "10",
                "tx": "20",
                "disabled": "false",
            }
        ],
        talkers=[],
        iface_rates={},
    )
    core = tree["children"][0]
    ether4 = next(p for p in core["children"] if p["label"] == "ether4")
    kinds = {c["kind"] for c in ether4["children"]}
    assert "router" in kinds
    assert "host" in kinds
    wg = next(p for p in core["children"] if p["label"] == "wireguard1")
    remote = wg["children"][0]
    assert remote["kind"] == "router"
    assert any(c["kind"] == "net" for c in remote["children"])
