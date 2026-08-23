"""Interface counter deltas to bits-per-second."""

from __future__ import annotations

from typing import Any


def as_int(value: Any, default: int = 0) -> int:
    if value is None or value == "":
        return default
    try:
        return int(str(value).replace(" ", ""))
    except (TypeError, ValueError):
        return default


def counter_delta(prev: int, curr: int) -> int:
    if curr >= prev:
        return curr - prev
    return curr


def compute_bps(prev_bytes: int, curr_bytes: int, dt_seconds: float) -> int:
    if dt_seconds <= 0:
        return 0
    return int(counter_delta(prev_bytes, curr_bytes) * 8 / dt_seconds)


def snapshot_rates(
    previous: dict[str, dict[str, Any]] | None,
    current: list[dict[str, Any]],
    now: float,
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    """Compute per-interface rates. previous maps name -> {rx_byte, tx_byte, ts}."""
    previous = previous or {}
    next_state: dict[str, dict[str, Any]] = {}
    rows: list[dict[str, Any]] = []
    for iface in current:
        name = iface.get("name")
        if not name:
            continue
        rx_byte = as_int(iface.get("rx-byte"))
        tx_byte = as_int(iface.get("tx-byte"))
        prev = previous.get(name)
        if not prev:
            rx_bps = tx_bps = 0
        else:
            dt = now - float(prev["ts"])
            rx_delta = counter_delta(prev["rx_byte"], rx_byte)
            tx_delta = counter_delta(prev["tx_byte"], tx_byte)
            # 同一秒计数器未刷新时沿用上次速率，避免曲线掉零
            if rx_delta == 0 and 0 < dt < 2.0:
                rx_bps = int(prev.get("rx_bps") or 0)
            else:
                rx_bps = compute_bps(prev["rx_byte"], rx_byte, dt)
            if tx_delta == 0 and 0 < dt < 2.0:
                tx_bps = int(prev.get("tx_bps") or 0)
            else:
                tx_bps = compute_bps(prev["tx_byte"], tx_byte, dt)
        next_state[name] = {
            "rx_byte": rx_byte,
            "tx_byte": tx_byte,
            "ts": now,
            "rx_bps": rx_bps,
            "tx_bps": tx_bps,
        }
        rows.append(
            {
                "name": name,
                "type": iface.get("type") or "",
                "comment": iface.get("comment") or "",
                "running": str(iface.get("running")).lower() == "true",
                "disabled": str(iface.get("disabled")).lower() == "true",
                "rx_byte": rx_byte,
                "tx_byte": tx_byte,
                "rx_bps": rx_bps,
                "tx_bps": tx_bps,
            }
        )
    rows.sort(key=lambda r: r["rx_bps"] + r["tx_bps"], reverse=True)
    return rows, next_state
