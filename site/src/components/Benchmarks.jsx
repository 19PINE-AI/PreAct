import { useState, useMemo } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import Reveal from './Reveal'
import {
  BENCHMARKS, ANDROID_TASKS, OSWORLD_TASKS, WEBARENA_TASKS,
} from '../data/benchmarks'
import './Benchmarks.css'

const TABS = ['androidworld', 'osworld', 'webarena']

export default function Benchmarks() {
  const [tab, setTab] = useState('androidworld')
  const [query, setQuery] = useState('')
  const [filter, setFilter] = useState('all') // all | pass | fail
  const [open, setOpen] = useState(null)

  const bench = BENCHMARKS[tab]

  const tasks = useMemo(() => {
    let list =
      tab === 'androidworld' ? ANDROID_TASKS : tab === 'osworld' ? OSWORLD_TASKS : WEBARENA_TASKS
    const q = query.trim().toLowerCase()
    if (q) {
      list = list.filter((t) => {
        const hay = `${t.id} ${t.intent || ''} ${t.desc || ''} ${t.app || ''}`.toLowerCase()
        return hay.includes(q)
      })
    }
    if (filter !== 'all') {
      list = list.filter((t) => statusOf(tab, t) === filter)
    }
    return list
  }, [tab, query, filter])

  const stats = useMemo(() => benchStats(tab), [tab])

  const switchTab = (t) => {
    setTab(t)
    setQuery('')
    setFilter('all')
    setOpen(null)
  }

  return (
    <section id="benchmarks">
      <div className="shell">
        <Reveal className="section-head">
          <span className="divider-num">§5 — TEST CASES &amp; BENCHMARKS</span>
          <h2>Every task we ran, browsable.</h2>
          <p>
            33 distinct tasks across three structurally different platforms — mobile, desktop, and
            web. Search, filter by outcome, and open any task for its goal, evaluator, and
            per-seed result.
          </p>
        </Reveal>

        {/* tabs */}
        <div className="bm__tabs">
          {TABS.map((t) => (
            <button key={t} className={`bm__tab ${tab === t ? 'is-active' : ''}`} onClick={() => switchTab(t)}>
              <span className="bm__tab-name">{BENCHMARKS[t].name}</span>
              <span className="bm__tab-sub mono">{BENCHMARKS[t].subset}</span>
            </button>
          ))}
        </div>

        {/* bench meta + stats */}
        <Reveal key={tab} className="bm__meta panel">
          <div className="bm__meta-left">
            <p className="bm__blurb">{bench.blurb}</p>
            <div className="bm__meta-chips">
              <span className="bm__chip mono"><b>CUA</b> {bench.cuaModel}</span>
              <span className="bm__chip mono"><b>env</b> {bench.container}</span>
            </div>
            <p className="bm__evalnote scrim">{bench.evalNote}</p>
          </div>
          <div className="bm__stat-ring">
            <Ring pct={stats.pct} tone={stats.tone} />
            <div className="bm__stat-meta">
              <span className="bm__stat-big mono">{stats.headline}</span>
              <span className="scrim">{stats.caption}</span>
            </div>
          </div>
        </Reveal>

        {/* controls */}
        <div className="bm__controls">
          <div className="bm__search">
            <span className="mono">/</span>
            <input
              type="text"
              placeholder={`search ${bench.name} tasks…`}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
          </div>
          <div className="bm__filters">
            {['all', 'pass', 'fail'].map((f) => (
              <button key={f} className={`bm__filter ${filter === f ? 'is-active' : ''} bm__filter--${f}`} onClick={() => setFilter(f)}>
                {f}
              </button>
            ))}
          </div>
          <span className="bm__count mono">{tasks.length} shown</span>
        </div>

        {/* task list */}
        <div className="bm__list">
          <AnimatePresence mode="popLayout">
            {tasks.map((t, i) => (
              <motion.div
                key={tab + (t.id ?? t.intent)}
                layout
                initial={{ opacity: 0, y: 14 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.97 }}
                transition={{ duration: 0.32, delay: Math.min(i * 0.015, 0.2) }}
              >
                {tab === 'androidworld' && <AndroidCard t={t} open={open} setOpen={setOpen} seeds={bench.seeds} />}
                {tab === 'osworld' && <OsworldCard t={t} open={open} setOpen={setOpen} />}
                {tab === 'webarena' && <WebarenaCard t={t} open={open} setOpen={setOpen} />}
              </motion.div>
            ))}
          </AnimatePresence>
          {tasks.length === 0 && <div className="bm__empty scrim mono">no tasks match — clear the filter</div>}
        </div>
      </div>
    </section>
  )
}

/* ── cards ──────────────────────────────────────────────── */
function AndroidCard({ t, open, setOpen, seeds }) {
  const isOpen = open === t.id
  const passes = t.warm.filter((w) => w.startsWith('PASS')).length
  return (
    <div className={`bm__card ${isOpen ? 'is-open' : ''}`} onClick={() => setOpen(isOpen ? null : t.id)}>
      <div className="bm__card-main">
        <div className="bm__card-id">
          <span className="bm__id-name">{t.id}</span>
          <span className="bm__app mono">{t.app}</span>
        </div>
        <p className="bm__desc">{t.desc}</p>
        <div className="bm__card-right">
          <div className="bm__seeds">
            {t.warm.map((w, i) => (
              <span key={i} className={`pill ${w.startsWith('PASS') ? 'pill-pass' : 'pill-fail'}`} title={`seed ${seeds[i]}`}>
                {w.includes('†') ? 'PASS†' : w}
              </span>
            ))}
          </div>
          {t.stable && <span className="bm__flag bm__flag--stable mono">stable fail</span>}
          {t.variance && <span className="bm__flag bm__flag--var mono">seed-variant</span>}
          {t.smokingGun && <span className="bm__flag bm__flag--gun mono">smoking-gun</span>}
        </div>
      </div>
      <AnimatePresence>
        {isOpen && (
          <motion.div className="bm__detail" initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }} exit={{ height: 0, opacity: 0 }} transition={{ duration: 0.3 }}>
            <div className="bm__detail-grid">
              <Field label="warm pass · seeds 42 / 100 / 1337" value={`${passes}/3 monotonicity seeds`} />
              {t.why && <Field label="why it fails" value={t.why} tone="fail" />}
              {t.smokingGun && <Field label="gate-OFF smoking-gun" value={`program ${t.smokingGun} — replays cov=100% but scores 0; the verify-gate filters it`} tone="fail" />}
              {t.warm.some((w) => w.includes('†')) && <Field label="† annotation" value="Live evaluator passed, but the verify-gate rejected the recompiled program on that seed (verify_score=0). The warm run still passed via RPA / hybrid / CUA." tone="pass" />}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

function OsworldCard({ t, open, setOpen }) {
  const isOpen = open === t.id
  return (
    <div className={`bm__card ${isOpen ? 'is-open' : ''}`} onClick={() => setOpen(isOpen ? null : t.id)}>
      <div className="bm__card-main">
        <div className="bm__card-id">
          <span className="bm__id-name mono">{t.id}</span>
          <span className="bm__app mono">{t.app}</span>
        </div>
        <p className="bm__desc">{t.desc}</p>
        <div className="bm__card-right">
          <span className={`pill ${t.mode === 'cua' ? 'pill-warn' : 'pill-pass'}`}>{t.mode}</span>
        </div>
      </div>
      <AnimatePresence>
        {isOpen && (
          <motion.div className="bm__detail" initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }} exit={{ height: 0, opacity: 0 }} transition={{ duration: 0.3 }}>
            <div className="bm__detail-grid">
              <Field label="full task id" value={t.fullId} mono />
              <Field label="evaluator" value={t.evalCriterion} />
              <Field label="warm replay mode" value={`${t.mode} — ${t.mode === 'rpa' ? 'pure state-machine replay' : t.mode === 'hybrid' ? 'replay then CUA recovery' : 'fresh CUA exploration'}`} tone={t.mode === 'cua' ? 'warn' : 'pass'} />
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

function WebarenaCard({ t, open, setOpen }) {
  const isOpen = open === t.id
  return (
    <div className={`bm__card ${isOpen ? 'is-open' : ''}`} onClick={() => setOpen(isOpen ? null : t.id)}>
      <div className="bm__card-main">
        <div className="bm__card-id">
          <span className="bm__id-name">task {t.id}</span>
          <span className={`bm__app mono ${t.family === 'review-count' ? 'signal-pass' : 'signal-replay'}`}>{t.family}</span>
        </div>
        <p className="bm__desc">{t.intent}</p>
        <div className="bm__card-right">
          <span className={`pill ${t.cold === 'PASS' ? 'pill-pass' : 'pill-fail'}`}>cold {t.cold}</span>
        </div>
      </div>
      <AnimatePresence>
        {isOpen && (
          <motion.div className="bm__detail" initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }} exit={{ height: 0, opacity: 0 }} transition={{ duration: 0.3 }}>
            <div className="bm__detail-grid">
              <Field label="reference answer" value={t.answer} mono tone="pass" />
              <Field label="eval type" value={t.eval} mono />
              <Field label="task family" value={t.family === 'review-count' ? 'review-counting — these compile into verifiable predicates and survive the gate (the warm-SR engine)' : 'bestseller analytics — answer depends on dynamic page state; inspect_screenshot returns make these lossy under gate-OFF'} tone={t.family === 'review-count' ? 'pass' : 'fail'} />
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

function Field({ label, value, mono, tone }) {
  return (
    <div className="bm__field">
      <span className="bm__field-lbl mono">{label}</span>
      <span className={`bm__field-val ${mono ? 'mono' : ''} ${tone ? `signal-${tone}` : ''}`}>{value}</span>
    </div>
  )
}

/* ── helpers ────────────────────────────────────────────── */
function statusOf(tab, t) {
  if (tab === 'androidworld') return t.warm.filter((w) => w.startsWith('PASS')).length >= 2 ? 'pass' : 'fail'
  if (tab === 'osworld') return 'pass' // all 6 pass under gate-ON warm
  return t.cold === 'PASS' ? 'pass' : 'fail'
}

function benchStats(tab) {
  if (tab === 'androidworld')
    return { pct: 73, tone: 'pass', headline: '11.0 / 15', caption: 'Gemini 3 Flash · 3-seed warm mean (73.3%)' }
  if (tab === 'osworld')
    return { pct: 83, tone: 'pass', headline: '5–6 / 6', caption: 'Claude Sonnet 4.6 · gate-ON warm' }
  return { pct: 58, tone: 'replay', headline: '7 / 12', caption: 'cold eval-SR · run-1 exploration' }
}

function Ring({ pct, tone }) {
  const r = 34
  const circ = 2 * Math.PI * r
  const dash = (pct / 100) * circ
  const color = `var(--${tone})`
  return (
    <svg className="bm__ring" viewBox="0 0 84 84" width="84" height="84">
      <circle cx="42" cy="42" r={r} fill="none" stroke="var(--line)" strokeWidth="6" />
      <motion.circle
        cx="42" cy="42" r={r} fill="none" stroke={color} strokeWidth="6" strokeLinecap="round"
        transform="rotate(-90 42 42)"
        initial={{ strokeDasharray: `0 ${circ}` }}
        whileInView={{ strokeDasharray: `${dash} ${circ}` }}
        viewport={{ once: true }}
        transition={{ duration: 1.1, ease: [0.22, 1, 0.36, 1] }}
      />
      <text x="42" y="47" textAnchor="middle" fill={color} fontSize="17" fontFamily="var(--font-mono)" fontWeight="600">{pct}%</text>
    </svg>
  )
}
