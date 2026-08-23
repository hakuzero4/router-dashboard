import { useEffect, useRef } from 'react'
import { axisUnit, formatClock } from '../lib/format.js'
import { cssVar, useTheme } from '../lib/theme.jsx'

function niceMax(value) {
  if (value <= 0) return 1
  const exp = 10 ** Math.floor(Math.log10(value))
  const scaled = value / exp
  const nice = scaled <= 1 ? 1 : scaled <= 2 ? 2 : scaled <= 5 ? 5 : 10
  return nice * exp
}

export default function TrafficChart({ points }) {
  const canvasRef = useRef(null)
  const { theme } = useTheme()

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const draw = () => {
      const dpr = window.devicePixelRatio || 1
      const width = canvas.clientWidth
      const height = canvas.clientHeight
      if (width === 0 || height === 0) return
      canvas.width = Math.floor(width * dpr)
      canvas.height = Math.floor(height * dpr)
      const ctx = canvas.getContext('2d')
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
      ctx.clearRect(0, 0, width, height)

      const data = points || []
      const pad = { l: 56, r: 16, t: 12, b: 28 }
      const chartW = width - pad.l - pad.r
      const chartH = height - pad.t - pad.b

      const rx = cssVar('--rx', '#4a9b82')
      const tx = cssVar('--tx', '#c4a574')
      const grid = cssVar('--grid', 'rgba(232,228,219,0.08)')
      const labelColor = cssVar('--label', 'rgba(232,228,219,0.38)')
      ctx.fillStyle = labelColor
      ctx.font = '11px "Geist Mono", ui-monospace, monospace'
      if (data.length < 2) {
        ctx.fillText('采样中，约两秒后出曲线', pad.l, height / 2)
        return
      }

      const rawMax = Math.max(1, ...data.flatMap((p) => [p.rx || 0, p.tx || 0]))
      const max = niceMax(rawMax * 1.05)
      const unit = axisUnit(max)
      const yOf = (v) => pad.t + chartH - (v / max) * chartH
      const xOf = (i) => pad.l + (i / (data.length - 1)) * chartW

      ctx.strokeStyle = grid
      ctx.lineWidth = 1
      const ticks = 5
      for (let i = 0; i <= ticks; i += 1) {
        const value = (max * (ticks - i)) / ticks
        const y = pad.t + (chartH * i) / ticks
        ctx.beginPath()
        ctx.moveTo(pad.l, y)
        ctx.lineTo(pad.l + chartW, y)
        ctx.stroke()
        ctx.fillStyle = labelColor
        ctx.textAlign = 'right'
        ctx.textBaseline = 'middle'
        const tickLabel = i === ticks ? `0.00 ${unit.suffix}` : `${(value / unit.div).toFixed(2)}`
        ctx.fillText(i === 0 ? `${(value / unit.div).toFixed(2)} ${unit.suffix}` : tickLabel, pad.l - 8, y)
      }

      const fill = (key, color) => {
        ctx.beginPath()
        data.forEach((p, i) => {
          const x = xOf(i)
          const y = yOf(p[key] || 0)
          if (i === 0) ctx.moveTo(x, y)
          else ctx.lineTo(x, y)
        })
        ctx.lineTo(xOf(data.length - 1), pad.t + chartH)
        ctx.lineTo(xOf(0), pad.t + chartH)
        ctx.closePath()
        const g = ctx.createLinearGradient(0, pad.t, 0, pad.t + chartH)
        g.addColorStop(0, `${color}40`)
        g.addColorStop(1, `${color}00`)
        ctx.fillStyle = g
        ctx.fill()

        ctx.beginPath()
        data.forEach((p, i) => {
          const x = xOf(i)
          const y = yOf(p[key] || 0)
          if (i === 0) ctx.moveTo(x, y)
          else ctx.lineTo(x, y)
        })
        ctx.strokeStyle = color
        ctx.lineWidth = 1.7
        ctx.stroke()
      }

      fill('rx', rx)
      fill('tx', tx)

      ctx.fillStyle = labelColor
      ctx.textAlign = 'center'
      ctx.textBaseline = 'top'
      const xTicks = 6
      for (let i = 0; i < xTicks; i += 1) {
        const idx = Math.round((i / (xTicks - 1)) * (data.length - 1))
        const point = data[idx]
        if (!point?.t) continue
        ctx.fillText(formatClock(point.t), xOf(idx), pad.t + chartH + 8)
      }
    }

    draw()
    const ro = new ResizeObserver(draw)
    ro.observe(canvas)
    return () => ro.disconnect()
  }, [points, theme])

  return <canvas ref={canvasRef} className="h-full w-full" />
}
