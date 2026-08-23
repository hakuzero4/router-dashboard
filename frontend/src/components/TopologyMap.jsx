import { useEffect, useMemo, useRef, useState } from 'react'
import { ArrowsInSimple, Minus, Plus } from '@phosphor-icons/react'
import { formatBps } from '../lib/format.js'
import { cssVar, useTheme } from '../lib/theme.jsx'

const MIN_SCALE = 0.4
const MAX_SCALE = 2.5
const COL = 198
const GAP = 12

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value))
}

const WIDTH = {
  cloud: 150,
  core: 168,
  port: 118,
  router: 168,
  peer: 150,
  host: 158,
  net: 138,
}
const HEIGHT = {
  cloud: 52,
  core: 58,
  port: 36,
  router: 54,
  peer: 48,
  host: 42,
  net: 34,
}

function nodeSize(kind) {
  return { w: WIDTH[kind] || 150, h: HEIGHT[kind] || 42 }
}

function walk(node, visit, parent = null) {
  visit(node, parent)
  for (const child of node.children || []) walk(child, visit, node)
}

function layout(root) {
  const measure = (node) => {
    const { h } = nodeSize(node.kind)
    const kids = node.children || []
    if (!kids.length) {
      node._h = h
      return h
    }
    let sum = 0
    kids.forEach((child, i) => {
      sum += measure(child)
      if (i) sum += GAP
    })
    node._h = Math.max(h, sum)
    return node._h
  }

  const place = (node, x, y) => {
    const { w, h } = nodeSize(node.kind)
    const kids = node.children || []
    node.x = x
    node.y = y + (node._h - h) / 2
    node.w = w
    node.h = h
    let cy = y
    for (const child of kids) {
      place(child, x + COL, cy)
      cy += child._h + GAP
    }
  }

  measure(root)
  place(root, 24, 24)
  const nodes = []
  const links = []
  walk(root, (node, parent) => {
    nodes.push(node)
    if (parent) {
      links.push({
        id: `${parent.id}->${node.id}`,
        from: parent,
        to: node,
        live: (node.down_bps || 0) + (node.up_bps || 0) + (parent.down_bps || 0) > 0,
      })
    }
  })
  const maxX = Math.max(...nodes.map((n) => n.x + n.w), 400)
  const maxY = Math.max(...nodes.map((n) => n.y + n.h), 200)
  return { nodes, links, width: maxX + 40, height: maxY + 32 }
}

function elbow(from, to) {
  const x1 = from.x + from.w
  const y1 = from.y + from.h / 2
  const x2 = to.x
  const y2 = to.y + to.h / 2
  const mid = x1 + (x2 - x1) * 0.45
  return `M ${x1} ${y1} H ${mid} V ${y2} H ${x2}`
}

function kindLabel(kind) {
  if (kind === 'router') return '子路由'
  if (kind === 'peer') return '隧道'
  if (kind === 'port') return '端口'
  if (kind === 'net') return '网段'
  if (kind === 'core') return '核心'
  if (kind === 'cloud') return '出口'
  return '终端'
}

export default function TopologyMap({ tree }) {
  const { theme } = useTheme()
  const [hover, setHover] = useState(null)
  const viewRef = useRef(null)
  const shellRef = useRef(null)
  const layerRef = useRef(null)
  const percentRef = useRef(null)
  const drag = useRef(null)
  const raf = useRef(0)
  const camera = useRef({ scale: 1, pan: { x: 0, y: 0 } })
  const packed = useMemo(() => (tree ? layout(structuredClone(tree)) : null), [tree])
  const palette = useMemo(
    () => ({
      rx: cssVar('--rx', '#4a9b82'),
      mute: cssVar('--mute', '#8c877c'),
      ink: cssVar('--ink', '#e8e4db'),
      line: cssVar('--node-line', '#2a2d31'),
    }),
    [theme],
  )

  const paint = () => {
    const { scale, pan } = camera.current
    const layer = layerRef.current
    const shell = shellRef.current
    if (layer) {
      layer.style.transform = `translate3d(${pan.x}px, ${pan.y}px, 0) scale(${scale})`
    }
    if (shell && packed) {
      shell.style.width = `${packed.width * scale}px`
      shell.style.height = `${packed.height * scale}px`
    }
    if (percentRef.current) {
      percentRef.current.textContent = `${Math.round(scale * 100)}%`
    }
  }

  const schedulePaint = () => {
    if (raf.current) return
    raf.current = window.requestAnimationFrame(() => {
      raf.current = 0
      paint()
    })
  }

  const zoomTo = (next, origin) => {
    const current = camera.current
    const view = viewRef.current
    const clamped = clamp(next, MIN_SCALE, MAX_SCALE)
    if (!view) {
      camera.current = { scale: clamped, pan: current.pan }
      paint()
      return
    }
    const factor = clamped / current.scale
    const px = origin?.x ?? view.clientWidth / 2
    const py = origin?.y ?? view.clientHeight / 2
    camera.current = {
      scale: clamped,
      pan: {
        x: px - (px - current.pan.x) * factor,
        y: py - (py - current.pan.y) * factor,
      },
    }
    paint()
  }

  const resetView = () => {
    camera.current = { scale: 1, pan: { x: 0, y: 0 } }
    paint()
  }

  useEffect(() => {
    paint()
  }, [packed])

  useEffect(() => {
    const el = viewRef.current
    if (!el) return undefined
    const onWheel = (event) => {
      if (!event.ctrlKey && !event.metaKey) return
      event.preventDefault()
      const rect = el.getBoundingClientRect()
      const factor = event.deltaY > 0 ? 1 / 1.12 : 1.12
      zoomTo(camera.current.scale * factor, {
        x: event.clientX - rect.left,
        y: event.clientY - rect.top,
      })
    }
    el.addEventListener('wheel', onWheel, { passive: false })
    return () => el.removeEventListener('wheel', onWheel)
  }, [packed])

  if (!tree) {
    return <div className="h-[320px] animate-pulse bg-ink/5" />
  }
  if (!packed?.nodes.length) {
    return <p className="py-16 text-sm text-mute">还没有桥接主机数据。</p>
  }

  const related = new Set()
  if (hover) {
    related.add(hover)
    packed.links.forEach((link) => {
      if (link.from.id === hover || link.to.id === hover) {
        related.add(link.from.id)
        related.add(link.to.id)
      }
    })
  }

  return (
    <div className="w-full">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <p className="font-mono text-[11px] text-mute">Ctrl + 滚轮缩放 · 拖动平移</p>
        <div className="flex items-center gap-1">
          <ZoomButton
            label="缩小"
            onClick={() => zoomTo(camera.current.scale / 1.25)}
          >
            <Minus size={12} />
          </ZoomButton>
          <span
            ref={percentRef}
            className="num min-w-[3.2rem] text-center font-mono text-xs text-ink/80"
          >
            100%
          </span>
          <ZoomButton
            label="放大"
            onClick={() => zoomTo(camera.current.scale * 1.25)}
          >
            <Plus size={12} />
          </ZoomButton>
          <ZoomButton label="复位" onClick={resetView}>
            <ArrowsInSimple size={12} />
            <span className="ml-1 hidden sm:inline">复位</span>
          </ZoomButton>
        </div>
      </div>
      <div
        ref={viewRef}
        className="topo-view relative w-full cursor-grab overflow-auto border border-line bg-panel"
        style={{ maxHeight: '70vh' }}
        onPointerDown={(event) => {
          if (event.button !== 0) return
          event.preventDefault()
          window.getSelection()?.removeAllRanges()
          event.currentTarget.setPointerCapture(event.pointerId)
          event.currentTarget.classList.add('cursor-grabbing', 'topo-dragging')
          drag.current = {
            x: event.clientX - camera.current.pan.x,
            y: event.clientY - camera.current.pan.y,
          }
        }}
        onPointerMove={(event) => {
          if (!drag.current) return
          camera.current.pan = {
            x: event.clientX - drag.current.x,
            y: event.clientY - drag.current.y,
          }
          schedulePaint()
        }}
        onPointerUp={(event) => {
          drag.current = null
          event.currentTarget.classList.remove('cursor-grabbing', 'topo-dragging')
        }}
        onPointerCancel={(event) => {
          drag.current = null
          event.currentTarget.classList.remove('cursor-grabbing', 'topo-dragging')
        }}
      >
        <div ref={shellRef} className="relative" style={{ width: packed.width, height: packed.height }}>
          <div
            ref={layerRef}
            style={{
              transform: 'translate3d(0,0,0) scale(1)',
              transformOrigin: '0 0',
              willChange: 'transform',
            }}
          >
            <svg
              viewBox={`0 0 ${packed.width} ${packed.height}`}
              width={packed.width}
              height={packed.height}
              className="block max-w-none"
              role="img"
              aria-label="终端与子路由连接图"
            >
              {packed.links.map((link) => {
                const active = !hover || related.has(link.from.id)
                return (
                  <path
                    key={link.id}
                    d={elbow(link.from, link.to)}
                    fill="none"
                    stroke={link.live ? palette.rx : palette.line}
                    strokeWidth={link.to.kind === 'router' ? 1.8 : 1.15}
                    strokeOpacity={active ? 1 : 0.18}
                    className={link.live ? 'topo-flow' : undefined}
                  />
                )
              })}
              {packed.nodes.map((node) => {
                const dim = hover && !related.has(node.id)
                return (
                  <g
                    key={node.id}
                    transform={`translate(${node.x} ${node.y})`}
                    opacity={dim ? 0.28 : 1}
                    onMouseEnter={() => {
                      if (!drag.current) setHover(node.id)
                    }}
                    onMouseLeave={() => {
                      if (!drag.current) setHover(null)
                    }}
                    className="cursor-pointer"
                  >
                    <rect
                      width={node.w}
                      height={node.h}
                      rx={node.kind === 'port' ? 2 : 4}
                      fill={fillFor(node.kind, theme)}
                      stroke={strokeFor(node.kind, node.online, theme)}
                      strokeWidth={node.kind === 'router' || node.kind === 'core' ? 1.4 : 1}
                    />
                    {node.kind === 'router' && (
                      <rect width="3" height={node.h} rx="1" fill={palette.rx} />
                    )}
                    <text
                      x="12"
                      y="15"
                      fill={palette.mute}
                      fontSize="9"
                      letterSpacing="0.16em"
                      fontFamily="Geist, ui-sans-serif, sans-serif"
                    >
                      {kindLabel(node.kind).toUpperCase()}
                    </text>
                    <text
                      x="12"
                      y={node.h > 44 ? 32 : 28}
                      fill={palette.ink}
                      fontSize={node.kind === 'core' ? 14 : 12}
                      fontFamily="Geist, ui-sans-serif, sans-serif"
                    >
                      {truncate(node.label, 14)}
                    </text>
                    {node.h > 44 && (
                      <text
                        x="12"
                        y="46"
                        fill={palette.mute}
                        fontSize="10"
                        fontFamily="Geist Mono, ui-monospace, monospace"
                      >
                        {truncate(node.sub || '', 22)}
                      </text>
                    )}
                  </g>
                )
              })}
            </svg>
            {hover && (
              <NodeTip node={packed.nodes.find((n) => n.id === hover)} />
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

function ZoomButton({ label, onClick, disabled, children }) {
  return (
    <button
      type="button"
      title={label}
      aria-label={label}
      disabled={disabled}
      onClick={onClick}
      className="inline-flex items-center border border-line bg-surface px-2 py-1 text-xs text-ink transition hover:border-ink/25 active:scale-[0.98] disabled:opacity-30"
    >
      {children}
    </button>
  )
}

function NodeTip({ node }) {
  if (!node) return null
  const kids = node.children || []
  const width = Math.max(node.w, 176)
  return (
    <div
      className="pointer-events-none absolute border border-rx/50 bg-surface px-2.5 py-2 shadow-[0_8px_24px_-12px_rgba(0,0,0,0.45)]"
      style={{
        left: node.x,
        top: node.y,
        width,
        minHeight: node.h,
      }}
    >
      <p className="text-[10px] uppercase tracking-[0.14em] text-mute">{kindLabel(node.kind)}</p>
      <p className="mt-0.5 text-sm tracking-tight text-ink">{node.label}</p>
      {node.ip && <p className="mt-0.5 font-mono text-[11px] text-mute">{node.ip}</p>}
      {(node.down_bps > 0 || node.up_bps > 0) && (
        <p className="num mt-1 text-[11px]">
          <span className="text-rx">{formatBps(node.down_bps)}</span>
          <span className="mx-1 text-mute">/</span>
          <span className="text-tx">{formatBps(node.up_bps)}</span>
        </p>
      )}
      {kids.length > 0 && <p className="mt-1 text-[11px] text-mute">{kids.length} 个下游</p>}
    </div>
  )
}

function fillFor(kind) {
  if (kind === 'core') return cssVar('--node-core', '#1a1e22')
  if (kind === 'router') return cssVar('--node-router', '#17211e')
  if (kind === 'port') return 'transparent'
  if (kind === 'cloud') return cssVar('--node-cloud', '#181b1f')
  return cssVar('--node', '#16181c')
}

function strokeFor(kind, online) {
  if (!online) return cssVar('--node-idle', '#5c534a')
  if (kind === 'core' || kind === 'router') return cssVar('--rx', '#4a9b82')
  if (kind === 'port') return cssVar('--line', '#3a3e43')
  return cssVar('--node-line', '#2f3338')
}

function truncate(text, max) {
  const value = String(text || '')
  return value.length > max ? `${value.slice(0, max - 1)}…` : value
}
