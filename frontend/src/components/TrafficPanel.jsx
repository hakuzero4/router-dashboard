import { useEffect, useMemo, useState } from 'react'
import { CaretDown } from '@phosphor-icons/react'
import TrafficChart from './TrafficChart.jsx'
import { formatBps } from '../lib/format.js'

const RANGES = [
  { id: '1m', minutes: 1, label: '1m' },
  { id: '5m', minutes: 5, label: '5m' },
  { id: '15m', minutes: 15, label: '15m' },
  { id: '1h', minutes: 60, label: '1h' },
]

export default function TrafficPanel({ data }) {
  const wanName = data?.wan?.name || ''
  const [iface, setIface] = useState('')
  const [range, setRange] = useState('1m')
  const [hist, setHist] = useState([])
  const selected = iface || wanName
  const ifaces = data?.interfaces || []
  const current = ifaces.find((row) => row.name === selected) || ifaces[0]
  const minutes = RANGES.find((row) => row.id === range)?.minutes || 1

  useEffect(() => {
    if (wanName && !iface) setIface(wanName)
  }, [wanName, iface])

  useEffect(() => {
    if (minutes <= 1) return undefined
    if (!selected) return undefined
    let cancelled = false
    const pull = async () => {
      try {
        const res = await fetch(`/api/history?iface=${encodeURIComponent(selected)}&minutes=${minutes}`)
        if (!res.ok) return
        const json = await res.json()
        if (!cancelled) setHist(json.points || [])
      } catch {
        /* keep last */
      }
    }
    pull()
    const id = window.setInterval(pull, 2000)
    return () => {
      cancelled = true
      window.clearInterval(id)
    }
  }, [selected, minutes])

  const points = useMemo(() => {
    if (minutes <= 1) return current?.spark || []
    return hist
  }, [minutes, current, hist])

  const up = Boolean(current?.running && !current?.disabled)
  const down = Boolean(current && !current.running && !current.disabled)

  return (
    <section className="border-b border-line px-5 py-5 md:px-8">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <p className="pr-2 text-[11px] uppercase tracking-[0.18em] text-mute">Traffic</p>
          <Select value={selected} onChange={setIface}>
            {ifaces.map((row) => (
              <option key={row.name} value={row.name}>
                {row.name}
              </option>
            ))}
          </Select>
          <Select value={range} onChange={setRange}>
            {RANGES.map((row) => (
              <option key={row.id} value={row.id}>
                {row.label}
              </option>
            ))}
          </Select>
          {current && (
            <span
              className={`inline-flex items-center gap-1.5 border px-2 py-1 font-mono text-[11px] ${
                up
                  ? 'border-rx/40 text-rx'
                  : down
                    ? 'border-danger/60 text-danger-text'
                    : 'border-line text-mute'
              }`}
            >
              <span className={`h-1.5 w-1.5 rounded-full ${up ? 'bg-rx' : down ? 'bg-danger' : 'bg-mute'}`} />
              {current.name} · {up ? 'up' : down ? 'down' : 'off'}
            </span>
          )}
        </div>
        <div className="flex items-center gap-4 font-mono text-xs">
          <span className="inline-flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full bg-rx" />
            <span className="text-mute">RX</span>
            <span className="text-rx">{formatBps(current?.rx_bps ?? 0)}</span>
          </span>
          <span className="inline-flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full bg-tx" />
            <span className="text-mute">TX</span>
            <span className="text-tx">{formatBps(current?.tx_bps ?? 0)}</span>
          </span>
        </div>
      </div>
      <div className="mt-4 h-[280px] min-h-[220px] md:h-[32vh]">
        {data ? <TrafficChart points={points} /> : <div className="h-full animate-pulse bg-ink/5" />}
      </div>
    </section>
  )
}

function Select({ value, onChange, children }) {
  return (
    <label className="relative inline-flex items-center">
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="appearance-none border border-line bg-surface py-1 pl-2.5 pr-7 font-mono text-xs text-ink outline-none transition hover:border-ink/25"
      >
        {children}
      </select>
      <CaretDown size={10} className="pointer-events-none absolute right-2 text-mute" />
    </label>
  )
}
