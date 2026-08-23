from rates import compute_bps, snapshot_rates


def test_compute_bps_from_byte_counters():
    assert compute_bps(1000, 2000, 1.0) == 8000
    assert compute_bps(1000, 2000, 2.0) == 4000


def test_counter_wrap_or_reboot_uses_current_as_delta():
    assert compute_bps(999999, 100, 1.0) == 800


def test_non_positive_dt_is_zero():
    assert compute_bps(0, 1000, 0) == 0
    assert compute_bps(0, 1000, -1) == 0


def test_snapshot_rates_needs_two_samples():
    current = [
        {
            "name": "pppoe-out1",
            "type": "pppoe-out",
            "running": "true",
            "disabled": "false",
            "rx-byte": "1000",
            "tx-byte": "2000",
        }
    ]
    rows, state = snapshot_rates(None, current, now=10.0)
    assert rows[0]["rx_bps"] == 0
    assert rows[0]["tx_bps"] == 0

    current[0]["rx-byte"] = "2000"
    current[0]["tx-byte"] = "4000"
    rows, state = snapshot_rates(state, current, now=11.0)
    assert rows[0]["rx_bps"] == 8000
    assert rows[0]["tx_bps"] == 16000
    assert rows[0]["running"] is True

    # 计数器未刷新时不要把速率打成 0
    rows, _ = snapshot_rates(state, current, now=11.5)
    assert rows[0]["rx_bps"] == 8000
    assert rows[0]["tx_bps"] == 16000
