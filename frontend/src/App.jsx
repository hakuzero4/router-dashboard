import { useEffect, useState } from 'react'
// talker expand state lives in TalkerTable, not here
import {
  ArrowDown,
  ArrowUp,
  Cpu,
  HardDrives,
  Moon,
  Pulse,
  ShareNetwork,
  Sun,
  WarningCircle,
} from '@phosphor-icons/react'
import TopologyMap from './components/TopologyMap.jsx'
import InterfaceBoard from './components/InterfaceBoard.jsx'
import TrafficPanel from './components/TrafficPanel.jsx'
import TalkerTable from './components/TalkerTable.jsx'
import { formatBps, formatBytes, formatMem, formatUptime } from './lib/format.js'
import { useTheme } from './lib/theme.jsx'

const POLL_MS = 1000
let pollTimer = 0

export default function App() {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const { theme, toggle } = useTheme()

  useEffect(() => {
    let cancelled = false
    const pull = async () => {
      try {
        const res = await fetch('/api/snapshot')
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        const json = await res.json()
        if (!cancelled) {
          setData(json)
          setError(json.ok ? null : json.error || '路由器暂无数据')
        }
      } catch (err) {
        if (!cancelled) setError(err.message || '无法连接面板后端')
      }
    }
    pull()
    window.clearInterval(pollTimer)
    pollTimer = window.setInterval(pull, POLL_MS)
    return () => {
      cancelled = true
      window.clearInterval(pollTimer)
    }
  }, [])

  const talkers = data?.talkers || []
  const activeTalkers = talkers.filter((row) => row.down_bps + row.up_bps > 0)
  const totals = talkers.reduce(
    (acc, row) => {
      acc.down += row.down_bps || 0
      acc.up += row.up_bps || 0
      acc.accDown += row.acc_down_bytes || 0
      acc.accUp += row.acc_up_bytes || 0
      return acc
    },
    { down: 0, up: 0, accDown: 0, accUp: 0 },
  )
  const wanDown = data?.wan?.rx_bps ?? totals.down
  const wanUp = data?.wan?.tx_bps ?? totals.up

  return (
    <div className="min-h-[100dvh] text-ink">
      <header className="flex flex-wrap items-center justify-between gap-3 border-b border-line px-5 py-2.5 md:px-8">
        <div className="flex flex-wrap items-baseline gap-3">
          <h1 className="text-sm tracking-tight">{data?.identity || 'hAP'}</h1>
          <span className="font-mono text-[11px] text-mute">{data?.board}</span>
        </div>
        <div className="flex flex-wrap items-center gap-x-5 gap-y-1 font-mono text-xs">
          <span className="inline-flex items-center gap-1.5" title="WAN 当前合计">
            <span className="text-mute">合计</span>
            <ArrowDown size={11} className="text-rx" />
            <span className="num text-rx">{formatBps(wanDown)}</span>
            <ArrowUp size={11} className="text-tx" />
            <span className="num text-tx">{formatBps(wanUp)}</span>
          </span>
          <span className="inline-flex items-center gap-1.5" title="所有终端累计流量">
            <span className="text-mute">累计</span>
            <span className="num text-rx">{formatBytes(totals.accDown)}</span>
            <span className="text-mute">/</span>
            <span className="num text-tx">{formatBytes(totals.accUp)}</span>
          </span>
        </div>
        <div className="flex flex-wrap items-center justify-end gap-x-5 gap-y-1 text-xs text-mute">
          <Status ok={Boolean(data?.ok)} error={error} />
          <Meta icon={Pulse} label="版本" value={data?.version || '—'} />
          <Meta icon={Cpu} label="CPU" value={data ? `${data.cpu_load}%` : '—'} />
          <Meta
            icon={HardDrives}
            label="内存"
            value={data ? formatMem(data.mem_used) : '—'}
          />
          <span className="hidden sm:inline">{formatUptime(data?.uptime)}</span>
          <button
            type="button"
            onClick={toggle}
            title={theme === 'dark' ? '切换浅色' : '切换深色'}
            aria-label={theme === 'dark' ? '切换浅色' : '切换深色'}
            className="inline-flex items-center gap-1 border border-line bg-surface px-2 py-1 text-ink transition hover:border-ink/25 active:scale-[0.98]"
          >
            {theme === 'dark' ? <Sun size={13} /> : <Moon size={13} />}
            <span className="hidden sm:inline">{theme === 'dark' ? '浅色' : '深色'}</span>
          </button>
        </div>
      </header>

      {error && (
        <div className="mx-5 mt-4 flex items-center gap-2 border border-danger/50 bg-danger/10 px-4 py-2 text-sm text-danger-text md:mx-8">
          <WarningCircle size={16} weight="bold" />
          {error}
        </div>
      )}

      <TrafficPanel data={data} />

      <section className="border-b border-line px-5 py-6 md:px-8">
        {data ? (
          <InterfaceBoard
            counts={data.type_counts}
            ports={data.physical_ports}
            interfaces={data.interfaces}
          />
        ) : (
          <div className="h-48 animate-pulse bg-ink/5" />
        )}
      </section>

      <section className="border-t border-line px-5 py-6 md:px-8">
        <div className="flex items-baseline justify-between gap-4">
          <div>
            <p className="flex items-center gap-2 text-[11px] uppercase tracking-[0.18em] text-mute">
              <ShareNetwork size={14} />
              连接图
            </p>
            <h2 className="mt-1 text-2xl tracking-tight">终端与子路由</h2>
          </div>
          <p className="max-w-xs text-right text-xs text-mute">
            从左到右：公网 → 路由 → 网口 → 子路由 / 终端。绿色竖条是子路由。
          </p>
        </div>
        <div className="mt-6">
          <TopologyMap tree={data?.topology} />
        </div>
      </section>

      <section className="border-t border-line px-5 py-6 md:px-8">
        <div className="flex items-baseline justify-between gap-4">
          <div>
            <p className="text-[11px] uppercase tracking-[0.18em] text-mute">占用排行</p>
            <h2 className="mt-1 text-2xl tracking-tight">谁在用网</h2>
          </div>
          <p className="font-mono text-xs text-mute">{activeTalkers.length} 台有流量 · {talkers.length} 台在连接表</p>
        </div>

        <TalkerTable talkers={talkers} />
      </section>
    </div>
  )
}

function Status({ ok, error }) {
  return (
    <span className="inline-flex items-center gap-2 text-ink">
      <span
        className={`live-dot inline-block h-1.5 w-1.5 rounded-full ${ok ? 'bg-rx' : 'bg-danger'}`}
      />
      {ok ? '实时' : error ? '离线' : '连接中'}
    </span>
  )
}

function Meta({ icon: Icon, label, value }) {
  return (
    <span className="inline-flex items-center gap-1.5">
      <Icon size={13} className="text-mute" />
      <span className="sr-only">{label}</span>
      <span className="font-mono text-ink/80">{value}</span>
    </span>
  )
}
