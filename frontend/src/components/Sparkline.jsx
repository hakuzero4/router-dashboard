import { cssVar, useTheme } from '../lib/theme.jsx'

export default function Sparkline({ points, className = '' }) {
  useTheme()
  const data = points || []
  const w = 88
  const h = 28
  if (data.length < 2) {
    return <svg viewBox={`0 0 ${w} ${h}`} className={className} width={w} height={h} />
  }
  const max = Math.max(1, ...data.flatMap((p) => [p.rx || 0, p.tx || 0]))
  const step = w / (data.length - 1)
  const path = (key, color) => {
    const d = data
      .map((p, i) => {
        const x = i * step
        const y = h - ((p[key] || 0) / max) * (h - 2) - 1
        return `${i === 0 ? 'M' : 'L'} ${x.toFixed(1)} ${y.toFixed(1)}`
      })
      .join(' ')
    return <path d={d} fill="none" stroke={color} strokeWidth="1.2" />
  }
  return (
    <svg viewBox={`0 0 ${w} ${h}`} className={className} width={w} height={h} aria-hidden>
      {path('rx', cssVar('--rx', '#4a9b82'))}
      {path('tx', cssVar('--tx', '#c4a574'))}
    </svg>
  )
}
