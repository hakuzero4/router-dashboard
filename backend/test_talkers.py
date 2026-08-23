from talkers import aggregate_talkers, host_and_direction, parse_networks, remember_peaks


LAN = ["10.1.1.0/24", "10.0.1.0/24"]


def test_outbound_nat_download_is_reply_rate():
    host, down, up, peer, down_b, up_b = host_and_direction(
        {
            "src-address": "10.1.1.19",
            "dst-address": "116.169.183.59",
            "reply-src-address": "116.169.183.59",
            "orig-rate": "24500",
            "repl-rate": "2200000",
            "orig-bytes": "1000",
            "repl-bytes": "80000",
        },
        parse_networks(LAN),
    )
    assert host == "10.1.1.19"
    assert down == 2200000
    assert up == 24500
    assert peer == "116.169.183.59"
    assert down_b == 80000
    assert up_b == 1000


def test_inbound_dstnat_uses_reply_src_as_lan_host():
    host, down, up, peer, down_b, up_b = host_and_direction(
        {
            "src-address": "182.84.240.125",
            "dst-address": "113.205.141.49",
            "reply-src-address": "10.1.1.50",
            "orig-rate": "38000",
            "repl-rate": "1400000",
            "orig-bytes": "200",
            "repl-bytes": "50",
        },
        parse_networks(LAN),
    )
    assert host == "10.1.1.50"
    assert down == 38000
    assert up == 1400000
    assert peer == "182.84.240.125"
    assert down_b == 200
    assert up_b == 50


def test_aggregate_merges_same_host_and_attaches_dhcp_name():
    conns = [
        {
            "src-address": "10.1.1.19",
            "dst-address": "1.1.1.1",
            "orig-rate": "100",
            "repl-rate": "1000",
        },
        {
            "src-address": "10.1.1.19",
            "dst-address": "8.8.8.8",
            "orig-rate": "50",
            "repl-rate": "4000",
        },
        {
            "src-address": "1.2.3.4",
            "dst-address": "5.6.7.8",
            "orig-rate": "999999",
            "repl-rate": "999999",
        },
    ]
    rows = aggregate_talkers(conns, LAN, names={"10.1.1.19": "iPhone"})
    assert len(rows) == 1
    assert rows[0]["ip"] == "10.1.1.19"
    assert rows[0]["name"] == "iPhone"
    assert rows[0]["down_bps"] == 5000
    assert rows[0]["up_bps"] == 150
    assert rows[0]["conns"] == 2
    assert rows[0]["peers"][0]["ip"] == "8.8.8.8"


def test_exclude_router_itself():
    conns = [
        {
            "src-address": "10.1.1.1",
            "dst-address": "1.1.1.1",
            "orig-rate": "100",
            "repl-rate": "200",
        }
    ]
    rows = aggregate_talkers(conns, LAN, exclude=["10.1.1.1"])
    assert rows == []


def test_remember_peaks_keeps_high_water_and_idle_hosts():
    store: dict = {}
    first = remember_peaks(
        [{"ip": "10.1.1.19", "name": "iPhone", "down_bps": 8000, "up_bps": 100, "conns": 1, "peers": []}],
        store,
    )
    assert first[0]["peak_down_bps"] == 8000
    assert first[0]["peak_total_bps"] == 8100

    second = remember_peaks(
        [{"ip": "10.1.1.19", "name": "iPhone", "down_bps": 200, "up_bps": 50, "conns": 1, "peers": []}],
        store,
    )
    assert second[0]["down_bps"] == 200
    assert second[0]["peak_down_bps"] == 8000
    assert second[0]["peak_up_bps"] == 100
    assert second[0]["peak_total_bps"] == 8100

    vol = remember_peaks(
        [
            {
                "ip": "10.1.1.19",
                "name": "iPhone",
                "down_bps": 200,
                "up_bps": 50,
                "down_bytes": 5000,
                "up_bytes": 100,
                "conns": 1,
                "peers": [],
            }
        ],
        store,
    )
    assert vol[0]["acc_down_bytes"] == 5000
    again = remember_peaks(
        [
            {
                "ip": "10.1.1.19",
                "name": "iPhone",
                "down_bps": 200,
                "up_bps": 50,
                "down_bytes": 8000,
                "up_bytes": 140,
                "conns": 1,
                "peers": [],
            }
        ],
        store,
    )
    assert again[0]["acc_down_bytes"] == 8000
    assert again[0]["acc_up_bytes"] == 140

    idle = remember_peaks([], store)
    assert len(idle) == 1
    assert idle[0]["ip"] == "10.1.1.19"
    assert idle[0]["down_bps"] == 0
    assert idle[0]["peak_down_bps"] == 8000
