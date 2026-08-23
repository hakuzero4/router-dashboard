from ifaces import attach_addresses, physical_ports, sort_interface_cards, type_counts


SAMPLE = [
    {"name": "wan", "type": "ether", "running": True, "disabled": False, "rx_bps": 10, "tx_bps": 1},
    {"name": "ether3", "type": "ether", "running": False, "disabled": False, "rx_bps": 0, "tx_bps": 0},
    {"name": "ether4", "type": "ether", "running": True, "disabled": False, "rx_bps": 5, "tx_bps": 5},
    {"name": "iptv", "type": "ether", "running": False, "disabled": True, "rx_bps": 0, "tx_bps": 0},
    {"name": "bridge1", "type": "bridge", "running": True, "disabled": False, "rx_bps": 1, "tx_bps": 1},
    {"name": "wifi1", "type": "wifi", "running": False, "disabled": True, "rx_bps": 0, "tx_bps": 0},
    {"name": "wireguard1", "type": "wg", "running": True, "disabled": False, "rx_bps": 2, "tx_bps": 3},
    {"name": "lo", "type": "loopback", "running": True, "disabled": False, "rx_bps": 0, "tx_bps": 0},
    {"name": "pppoe-out1", "type": "pppoe-out", "running": True, "disabled": False, "rx_bps": 8, "tx_bps": 2},
]


def test_type_counts_groups_wifi_and_lists_all_buckets():
    counts = type_counts(SAMPLE)
    by_key = {row["key"]: row["count"] for row in counts}
    assert by_key["ether"] == 4
    assert by_key["wifi"] == 1
    assert by_key["bridge"] == 1
    assert by_key["wg"] == 1
    assert by_key["loopback"] == 1
    assert by_key["pppoe-out"] == 1
    assert counts[0]["key"] == "ether"


def test_physical_ports_are_ethernet_in_panel_order():
    ports = physical_ports(SAMPLE)
    assert [p["name"] for p in ports] == ["wan", "ether3", "ether4", "iptv"]
    assert ports[0]["running"] is True
    assert ports[1]["running"] is False
    assert ports[-1]["disabled"] is True


def test_attach_addresses_uses_actual_interface():
    rows = attach_addresses(
        SAMPLE,
        [
            {"address": "10.1.1.1/24", "interface": "bridge1", "actual-interface": "bridge1"},
            {"address": "113.205.141.49/32", "interface": "pppoe-out1", "actual-interface": "pppoe-out1"},
        ],
    )
    by_name = {r["name"]: r["addresses"] for r in rows}
    assert by_name["bridge1"] == ["10.1.1.1/24"]
    assert by_name["pppoe-out1"] == ["113.205.141.49/32"]
    assert by_name["ether3"] == []


def test_cards_put_live_ethers_before_disabled():
    names = [r["name"] for r in sort_interface_cards(SAMPLE)]
    assert names[0] == "wan"
    assert names.index("wan") < names.index("ether3")
    assert names.index("ether4") < names.index("wifi1")
    assert names[-2:] == ["iptv", "wifi1"]
