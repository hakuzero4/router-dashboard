import { useMemo, useState } from 'react'
import { ArrowDown, ArrowUp } from '@phosphor-icons/react'
import Sparkline from './Sparkline.jsx'
import { formatBps } from '../lib/format.js'
import { cssVar, useTheme } from '../lib/theme.jsx'

export default function InterfaceBoard({ counts, ports, interfaces }) {
  useTheme()
  const [filter, setFilter] = useState(null)
  const cards = useMemo(() => {
    const rows = interfaces || []
    if (!filter) return rows
    if (filter === 'wifi') return rows.filter((row) => row.type === 'wifi' || row.type === 'wlan')
    return rows.filter((row) => row.type === filter)
  }, [interfaces, filter])

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 gap-px bg-line lg:grid-cols-[minmax(0,0.7fr)_minmax(0,1.3fr)]">
        <TypeCounts counts={counts || []} active={filter} onPick={setFilter} />
        <PhysicalPorts ports={ports || []} />
      </div>
      <div>
        <div className="flex items-baseline justify-between gap-4">
          <p className="text-[11px] uppercase tracking-[0.18em] text-mute">
            接口
            <span className="ml-2 font-mono text-ink/70">{cards.length}</span>
          </p>
          {filter && (
            <button
              type="button"
              onClick={() => setFilter(null)}
              className="text-xs text-mute transition hover:text-ink active:scale-[0.98]"
            >
              显示全部
            </button>
          )}
        </div>
        {cards.length === 0 ? (
          <p className="mt-8 text-sm text-mute">没有这类接口。</p>
        ) : (
          <ul className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4">
            {cards.map((iface) => (
              <li key={iface.name}>
                <IfaceCard iface={iface} />
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}

function TypeCounts({ counts, active, onPick }) {
  return (
    <div className="bg-bg px-5 py-5 md:px-6">
      <p className="text-[11px] uppercase tracking-[0.18em] text-mute">接口类型</p>
      <div className="mt-4 flex flex-wrap gap-2">
        {counts.map((row) => {
          const on = active === row.key
          return (
            <button
              key={row.key}
              type="button"
              onClick={() => onPick(on ? null : row.key)}
              className={`min-w-[4.5rem] border px-3 py-2 text-left transition active:scale-[0.98] ${
                on ? 'border-rx/70 bg-rx/10' : 'border-line bg-surface hover:border-ink/20'
              }`}
            >
              <p className="text-[10px] uppercase tracking-[0.14em] text-mute">{row.label}</p>
              <p className="num mt-1 text-2xl tracking-tight">{row.count}</p>
            </button>
          )
        })}
      </div>
    </div>
  )
}

function PhysicalPorts({ ports }) {
  return (
    <div className="bg-bg px-5 py-5 md:px-8">
      <p className="text-[11px] uppercase tracking-[0.18em] text-mute">物理网口</p>
      {ports.length === 0 ? (
        <p className="mt-6 text-sm text-mute">没有以太网口。</p>
      ) : (
        <div className="mt-5 flex flex-wrap items-end gap-5">
          {ports.map((port) => (
            <Rj45 key={port.name} port={port} />
          ))}
        </div>
      )}
    </div>
  )
}

function Rj45({ port }) {
  const down = !port.running
  const color = port.disabled ? cssVar('--node-idle', '#5c534a') : down ? cssVar('--danger', '#b56a52') : cssVar('--rx', '#4a9b82')
  const jack = cssVar('--surface', '#16181c')
  const well = cssVar('--bg', '#121417')
  return (
    <div className="flex flex-col items-center gap-2">
      <svg viewBox="0 0 44 40" width="44" height="40" aria-hidden>
        <rect x="3.5" y="3.5" width="37" height="33" rx="3.5" fill={jack} stroke={color} strokeWidth="1.6" />
        <rect x="11" y="9" width="22" height="16" rx="1.2" fill={well} stroke={color} strokeWidth="1.1" />
        {[0, 1, 2, 3, 4, 5, 6].map((i) => (
          <rect key={i} x={13 + i * 2.6} y="11.5" width="1.5" height="9" rx="0.3" fill={color} opacity="0.9" />
        ))}
        <rect x="16" y="28" width="12" height="3.2" rx="0.6" fill={color} opacity="0.55" />
      </svg>
      <span className="font-mono text-[10px] tracking-wide" style={{ color }}>
        {port.name}
      </span>
    </div>
  )
}

function IfaceCard({ iface }) {
  const up = iface.running && !iface.disabled
  const down = !iface.running && !iface.disabled
  const border = up ? 'border-rx/45' : down ? 'border-danger/70' : 'border-line'
  const address = (iface.addresses && iface.addresses[0]) || ''
  return (
    <article className={`border bg-surface p-3.5 ${border}`}>
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="flex items-center gap-2 text-sm tracking-tight">
            <span
              className={`inline-block h-1.5 w-1.5 rounded-full ${
                up ? 'bg-rx' : down ? 'bg-danger' : 'bg-mute'
              }`}
            />
            <span className="truncate">{iface.name}</span>
          </p>
          <p className="mt-0.5 font-mono text-[10px] uppercase tracking-wide text-mute">
            {iface.type}
            {iface.comment ? ` · ${iface.comment}` : ''}
          </p>
        </div>
        <Sparkline points={iface.spark} />
      </div>
      <p className="mt-2 truncate font-mono text-[11px] text-mute">{address || '—'}</p>
      <div className="mt-3 grid grid-cols-[auto_1fr] gap-x-2 gap-y-1 font-mono text-xs">
        <span className="text-mute">
          <ArrowDown size={11} className="inline -mt-0.5" />
        </span>
        <span className="num text-rx">{formatBps(iface.rx_bps)}</span>
        <span className="text-mute">
          <ArrowUp size={11} className="inline -mt-0.5" />
        </span>
        <span className="num text-tx">{formatBps(iface.tx_bps)}</span>
      </div>
    </article>
  )
}
