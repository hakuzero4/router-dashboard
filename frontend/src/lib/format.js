export function formatBps(value, digits = 1) {
  const n = Number(value) || 0
  const abs = Math.abs(n)
  if (abs < 1000) return `${Math.round(n)} bps`
  if (abs < 1_000_000) return `${(n / 1000).toFixed(digits)} Kbps`
  if (abs < 1_000_000_000) return `${(n / 1_000_000).toFixed(digits)} Mbps`
  return `${(n / 1_000_000_000).toFixed(2)} Gbps`
}

export function formatBytes(value) {
  const n = Number(value) || 0
  if (n < 1024) return `${n} B`
  if (n < 1024 ** 2) return `${(n / 1024).toFixed(1)} KB`
  if (n < 1024 ** 3) return `${(n / 1024 ** 2).toFixed(1)} MB`
  if (n < 1024 ** 4) return `${(n / 1024 ** 3).toFixed(1)} GB`
  return `${(n / 1024 ** 4).toFixed(2)} TB`
}

export function formatMem(bytes) {
  const n = Number(bytes) || 0
  return `${(n / 1024 ** 3).toFixed(2)} GB`
}

export function formatUptime(raw) {
  if (!raw) return '—'
  return String(raw).replace(/([0-9]+)([a-z]+)/g, '$1$2 ')
}

export function formatClock(ts) {
  if (!ts) return ''
  const date = new Date(Number(ts) * 1000)
  if (Number.isNaN(date.getTime())) return ''
  return date.toLocaleTimeString('en-US', {
    hour: 'numeric',
    minute: '2-digit',
    second: '2-digit',
  })
}

export function axisUnit(maxBps) {
  if (maxBps >= 1_000_000) return { div: 1_000_000, suffix: 'Mbps' }
  if (maxBps >= 1000) return { div: 1000, suffix: 'Kbps' }
  return { div: 1, suffix: 'bps' }
}

export function share(part, total) {
  if (!total) return 0
  return Math.min(100, Math.max(0, (part / total) * 100))
}
