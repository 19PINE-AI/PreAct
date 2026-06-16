import { motion } from 'framer-motion'

// Animated state-machine loop in the hero backdrop. Signal pulses travel the
// compile-extend-replace cycle: select → replay → fallback → compile → gate → store.
const NODES = [
  { id: 'goal', x: 90, y: 230, label: 'task', tone: 'var(--ink-soft)' },
  { id: 'sel', x: 250, y: 150, label: 'find', tone: 'var(--replay)' },
  { id: 'replay', x: 430, y: 110, label: 'replay', tone: 'var(--replay)' },
  { id: 'cua', x: 430, y: 300, label: 'agent', tone: 'var(--amber)' },
  { id: 'compile', x: 620, y: 250, label: 'compile', tone: 'var(--ink-soft)' },
  { id: 'gate', x: 770, y: 150, label: 'check', tone: 'var(--pass)' },
  { id: 'corpus', x: 770, y: 330, label: 'library', tone: 'var(--pass)' },
]
const EDGES = [
  ['goal', 'sel'], ['sel', 'replay'], ['replay', 'cua'], ['sel', 'cua'],
  ['cua', 'compile'], ['compile', 'gate'], ['gate', 'corpus'], ['corpus', 'sel'],
]
const pt = (id) => NODES.find((n) => n.id === id)

export default function HeroGraph() {
  return (
    <svg className="hero__graph" viewBox="0 0 880 440" preserveAspectRatio="xMidYMid slice" aria-hidden>
      <defs>
        <linearGradient id="edgeGrad" x1="0" x2="1">
          <stop offset="0" stopColor="var(--replay)" stopOpacity="0.5" />
          <stop offset="1" stopColor="var(--pass)" stopOpacity="0.5" />
        </linearGradient>
      </defs>
      {EDGES.map(([a, b], i) => {
        const p1 = pt(a)
        const p2 = pt(b)
        return (
          <g key={i}>
            <line x1={p1.x} y1={p1.y} x2={p2.x} y2={p2.y} stroke="var(--line-strong)" strokeWidth="1" />
            <motion.circle
              r="3.4"
              fill="url(#edgeGrad)"
              initial={{ cx: p1.x, cy: p1.y, opacity: 0 }}
              animate={{ cx: [p1.x, p2.x], cy: [p1.y, p2.y], opacity: [0, 1, 0] }}
              transition={{ duration: 2.2, repeat: Infinity, delay: i * 0.5, ease: 'easeInOut' }}
            />
          </g>
        )
      })}
      {NODES.map((n, i) => (
        <g key={n.id}>
          <motion.circle
            cx={n.x}
            cy={n.y}
            r="6.5"
            fill={n.tone}
            initial={{ scale: 0, opacity: 0 }}
            animate={{ scale: 1, opacity: 0.9 }}
            transition={{ delay: 0.4 + i * 0.1, duration: 0.5 }}
          />
          <motion.circle
            cx={n.x}
            cy={n.y}
            r="6.5"
            fill="none"
            stroke={n.tone}
            strokeWidth="1.4"
            initial={{ scale: 1, opacity: 0.6 }}
            animate={{ scale: [1, 2.6], opacity: [0.5, 0] }}
            transition={{ duration: 2.4, repeat: Infinity, delay: i * 0.3 }}
          />
          <text x={n.x} y={n.y - 14} fill={n.tone} fontSize="10.5" fontFamily="var(--font-mono)" textAnchor="middle" opacity="0.7">
            {n.label}
          </text>
        </g>
      ))}
    </svg>
  )
}
