import { motion } from 'framer-motion'
import { GATE_ABLATION } from '../../data/results'

// Diverging bar chart: cold→warm Δ with the gate ON (pass) vs OFF (fail),
// per platform, with the diff-of-deltas annotation. The paper's central figure,
// rebuilt as live SVG.
export default function GateChart() {
  const W = 720
  const H = 360
  const padX = 70
  const padTop = 36
  const padBot = 56
  const plotH = H - padTop - padBot
  const yMin = -8.2
  const yMax = 3
  const y = (v) => padTop + ((yMax - v) / (yMax - yMin)) * plotH
  const groupW = (W - padX * 2) / GATE_ABLATION.length
  const barW = 30
  const gap = 10
  const ticks = [2, 0, -2, -4, -6, -8]

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="gatechart" role="img" aria-label="Cross-platform verify-gate diff-of-deltas">
      {/* grid + axis */}
      {ticks.map((t) => (
        <g key={t}>
          <line x1={padX} x2={W - padX} y1={y(t)} y2={y(t)} stroke="var(--line)" strokeDasharray={t === 0 ? '0' : '3 4'} strokeWidth={t === 0 ? 1.4 : 1} />
          <text x={padX - 12} y={y(t) + 4} textAnchor="end" fontSize="11" fontFamily="var(--font-mono)" fill="var(--ink-mute)">{t}</text>
        </g>
      ))}
      <text x={20} y={padTop - 14} fontSize="11" fontFamily="var(--font-mono)" fill="var(--ink-soft)">Δ tasks</text>

      {GATE_ABLATION.map((d, i) => {
        const cx = padX + groupW * i + groupW / 2
        const onX = cx - barW - gap / 2
        const offX = cx + gap / 2
        return (
          <g key={d.platform}>
            {/* ON bar */}
            <Bar x={onX} w={barW} v={d.on} y={y} y0={y(0)} fill="var(--pass)" delay={i * 0.12} />
            <text x={onX + barW / 2} y={d.on >= 0 ? y(d.on) - 8 : y(d.on) + 16} textAnchor="middle" fontSize="11" fontFamily="var(--font-mono)" fill="var(--pass)" fontWeight="600">{d.on > 0 ? '+' : ''}{d.on}</text>
            {/* OFF bar */}
            <Bar x={offX} w={barW} v={d.off} y={y} y0={y(0)} fill="var(--fail)" delay={i * 0.12 + 0.06} />
            <text x={offX + barW / 2} y={y(d.off) + 16} textAnchor="middle" fontSize="11" fontFamily="var(--font-mono)" fill="var(--fail)" fontWeight="600">{d.off}</text>

            {/* diff annotation */}
            <text x={cx} y={padTop - 18} textAnchor="middle" fontSize="12" fontFamily="var(--font-mono)" fill="var(--ink)" fontWeight="600">diff {d.diff}</text>

            {/* platform label */}
            <text x={cx} y={H - 30} textAnchor="middle" fontSize="13" fontFamily="var(--font-display)" fill="var(--ink)" fontWeight="700">{d.platform}</text>
            <text x={cx} y={H - 14} textAnchor="middle" fontSize="9.5" fontFamily="var(--font-mono)" fill="var(--ink-mute)">{d.sub}</text>
          </g>
        )
      })}
    </svg>
  )
}

function Bar({ x, w, v, y, y0, fill, delay }) {
  const top = v >= 0 ? y(v) : y0
  const h = Math.abs(y(v) - y0)
  return (
    <motion.rect
      x={x}
      width={w}
      rx="2"
      fill={fill}
      initial={{ height: 0, y: y0 }}
      whileInView={{ height: h, y: top }}
      viewport={{ once: true }}
      transition={{ duration: 0.8, delay, ease: [0.22, 1, 0.36, 1] }}
      opacity="0.92"
    />
  )
}
