import { useMemo, useState } from 'react'
import { CaretDown, CaretUp } from '@phosphor-icons/react'
import { formatBps, formatBytes } from '../lib/format.js'

const COLUMNS = [
  { key: 'name', label: '主机', kind: 'text' },
  { key: 'ip', label: 'IP', kind: 'text' },
  { key: 'down_bps', label: '下载', kind: 'rate', tone: 'rx' },
  { key: 'up_bps', label: '上传', kind: 'rate', tone: 'tx' },
  { key: 'acc_down_bytes', label: '已下', kind: 'bytes', tone: 'rx' },
  { key: 'acc_up_bytes', label: '已上', kind: 'bytes', tone: 'tx' },
  { key: 'acc_total_bytes', label: '累计', kind: 'bytes' },
  { key: 'peak_down_bps', label: '峰值↓', kind: 'rate', tone: 'rx' },
  { key: 'peak_up_bps', label: '峰值↑', kind: 'rate', tone: 'tx' },
  { key: 'conns', label: '会话', kind: 'num' },
  { key: 'peer', label: '主要对端', kind: 'text' },
]

function valueOf(row, key) {
  if (key === 'total') return (row.down_bps || 0) + (row.up_bps || 0)
  if (key === 'peer') return row.peers?.[0]?.ip || ''
  return row[key] ?? ''
}

export default function TalkerTable({ talkers }) {
  const [sortKey, setSortKey] = useState('acc_total_bytes')
  const [sortDir, setSortDir] = useState('desc')
  const [openIp, setOpenIp] = useState(null)

  const rows = useMemo(() => {
    const copy = (talkers || []).map((row) => ({
      ...row,
      total: (row.down_bps || 0) + (row.up_bps || 0),
      acc_down_bytes: row.acc_down_bytes || 0,
      acc_up_bytes: row.acc_up_bytes || 0,
      acc_total_bytes: (row.acc_down_bytes || 0) + (row.acc_up_bytes || 0),
      peak_down_bps: row.peak_down_bps || 0,
      peak_up_bps: row.peak_up_bps || 0,
      peak_total_bps: row.peak_total_bps || 0,
    }))
    copy.sort((a, b) => {
      const av = valueOf(a, sortKey)
      const bv = valueOf(b, sortKey)
      let cmp = 0
      if (typeof av === 'number' && typeof bv === 'number') cmp = av - bv
      else cmp = String(av).localeCompare(String(bv), 'zh')
      return sortDir === 'asc' ? cmp : -cmp
    })
    return copy
  }, [talkers, sortKey, sortDir])

  const onSort = (key) => {
    if (sortKey === key) {
      setSortDir((dir) => (dir === 'desc' ? 'asc' : 'desc'))
      return
    }
    setSortKey(key)
    setSortDir(key === 'name' || key === 'ip' || key === 'peer' ? 'asc' : 'desc')
  }

  const summary = useMemo(() => {
    return (talkers || []).reduce(
      (acc, row) => {
        acc.down += row.down_bps || 0
        acc.up += row.up_bps || 0
        acc.accDown += row.acc_down_bytes || 0
        acc.accUp += row.acc_up_bytes || 0
        acc.peak += row.peak_total_bps || 0
        if ((row.down_bps || 0) + (row.up_bps || 0) > 0) acc.live += 1
        return acc
      },
      { down: 0, up: 0, accDown: 0, accUp: 0, peak: 0, live: 0 },
    )
  }, [talkers])

  if (!talkers?.length) {
    return (
      <p className="mt-10 max-w-md text-sm text-mute">
        还没有会话数据。确认连接跟踪开着，且 REST 用户有 read 权限。
      </p>
    )
  }

  return (
    <div className="mt-6">
      <div className="mb-4 grid grid-cols-2 gap-x-6 gap-y-2 border border-line px-4 py-3 md:grid-cols-4">
        <Stat label="当前下载" value={formatBps(summary.down)} tone="rx" />
        <Stat label="当前上传" value={formatBps(summary.up)} tone="tx" />
        <Stat label="累计已下" value={formatBytes(summary.accDown)} tone="rx" />
        <Stat label="累计已上" value={formatBytes(summary.accUp)} tone="tx" />
      </div>
      <div className="overflow-x-auto">
      <table className="w-full min-w-[980px] text-left">
        <thead>
          <tr className="border-b border-line text-[11px] uppercase tracking-[0.14em] text-mute">
            {COLUMNS.map((col) => {
              const active = sortKey === col.key
              return (
                <th key={col.key} className="pb-2 pr-3 font-normal">
                  <button
                    type="button"
                    onClick={() => onSort(col.key)}
                    className={`inline-flex items-center gap-1 transition hover:text-ink ${
                      active ? 'text-ink' : ''
                    }`}
                  >
                    {col.label}
                    {active ? (
                      sortDir === 'desc' ? (
                        <CaretDown size={10} />
                      ) : (
                        <CaretUp size={10} />
                      )
                    ) : (
                      <span className="inline-block w-2.5" />
                    )}
                  </button>
                </th>
              )
            })}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => {
            const open = openIp === row.ip
            const top = row.peers?.[0]
            return (
              <tr
                key={row.ip}
                className="border-t border-line/80 align-top hover:bg-ink/[0.04]"
                onClick={() => setOpenIp(open ? null : row.ip)}
              >
                <td className="py-2.5 pr-3 text-sm">{row.name}</td>
                <td className="py-2.5 pr-3 font-mono text-[11px] text-mute">{row.ip}</td>
                <RateCell value={row.down_bps} tone="rx" />
                <RateCell value={row.up_bps} tone="tx" />
                <ByteCell value={row.acc_down_bytes} tone="rx" />
                <ByteCell value={row.acc_up_bytes} tone="tx" />
                <ByteCell value={row.acc_total_bytes} />
                <RateCell value={row.peak_down_bps} tone="rx" muted />
                <RateCell value={row.peak_up_bps} tone="tx" muted />
                <td className="num py-2.5 pr-3 text-mute">{row.conns}</td>
                <td className="py-2.5 text-sm text-mute">
                  {top ? (
                    <span>
                      {top.ip}
                      <span className="ml-2 font-mono text-[11px] text-rx">{formatBps(top.down_bps)}</span>
                    </span>
                  ) : (
                    '—'
                  )}
                  {open && row.peers?.length > 1 && (
                    <ul className="mt-2 space-y-1 font-mono text-[11px]">
                      {row.peers.slice(1).map((peer) => (
                        <li key={peer.ip}>
                          {peer.ip}
                          <span className="ml-2 text-rx">{formatBps(peer.down_bps)}</span>
                          <span className="ml-1 text-tx">{formatBps(peer.up_bps)}</span>
                        </li>
                      ))}
                    </ul>
                  )}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
      </div>
    </div>
  )
}

function Stat({ label, value, tone }) {
  const color = tone === 'rx' ? 'text-rx' : tone === 'tx' ? 'text-tx' : 'text-ink'
  return (
    <div>
      <p className="text-[11px] uppercase tracking-[0.14em] text-mute">{label}</p>
      <p className={`num mt-1 text-lg ${color}`}>{value}</p>
    </div>
  )
}

function RateCell({ value, tone, muted }) {
  const color = muted ? 'text-mute' : tone === 'rx' ? 'text-rx' : tone === 'tx' ? 'text-tx' : 'text-ink/80'
  return <td className={`num py-2.5 pr-3 ${color}`}>{formatBps(value || 0)}</td>
}

function ByteCell({ value, tone }) {
  const color = tone === 'rx' ? 'text-rx' : tone === 'tx' ? 'text-tx' : 'text-ink/80'
  return <td className={`num py-2.5 pr-3 ${color}`}>{formatBytes(value || 0)}</td>
}
