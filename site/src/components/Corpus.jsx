import { useState, useMemo } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import Reveal from './Reveal'
import { CORPUS } from '../data/corpus'
import './Corpus.css'

// Friendly app names for the package ids that show up in the corpus.
const APP_NAMES = {
  'com.google.android.contacts': 'Contacts',
  'com.google.android.deskclock': 'Clock',
  'com.google.android.documentsui': 'Files',
  'com.android.camera2': 'Camera',
  'com.android.chrome': 'Chrome',
  'com.android.settings': 'Settings',
  'net.gsantner.markor': 'Markor (notes)',
  'com.dimowner.audiorecorder': 'Audio Recorder',
  'com.arduia.expense': 'Pro Expense',
  'com.flauschcode.broccoli': 'Broccoli (recipes)',
  'com.simplemobiletools.calendar.pro': 'Simple Calendar',
  'com.simplemobiletools.draw.pro': 'Simple Draw',
  'com.simplemobiletools.gallery.pro': 'Simple Gallery',
  'code.name.monkey.retromusic': 'Retro Music',
  'net.osmand': 'OsmAnd (maps)',
}
const appLabel = (app) => APP_NAMES[app] || app

const FILTERS = [
  { id: 'all', label: 'All' },
  { id: 'android', label: 'Phone' },
  { id: 'desktop', label: 'Desktop' },
]

export default function Corpus() {
  const [filter, setFilter] = useState('all')
  const [query, setQuery] = useState('')
  const [sel, setSel] = useState(0)

  const list = useMemo(() => {
    const q = query.trim().toLowerCase()
    return CORPUS.filter((p) => {
      if (filter !== 'all' && p.platform !== filter) return false
      if (!q) return true
      return (p.task + ' ' + p.app + ' ' + appLabel(p.app)).toLowerCase().includes(q)
    })
  }, [filter, query])

  // Keep the selection valid as the filter changes.
  const active = list[Math.min(sel, list.length - 1)] || null
  const counts = {
    all: CORPUS.length,
    android: CORPUS.filter((p) => p.platform === 'android').length,
    desktop: CORPUS.filter((p) => p.platform === 'desktop').length,
  }

  return (
    <section id="corpus">
      <div className="shell">
        <Reveal className="section-head">
          <span className="divider-num">§ BROWSE — THE REAL CORPUS</span>
          <h2>Every program here was learned by the agent.</h2>
          <p>
            These are {CORPUS.length} actual programs the agent saved while running real benchmark
            tasks across a phone and a desktop. Each one is a small graph: at every step it checks
            that the screen looks right, then performs an action. Pick one to see how it works.
          </p>
        </Reveal>

        <div className="corpus__bar">
          <div className="corpus__filters">
            {FILTERS.map((f) => (
              <button
                key={f.id}
                className={`corpus__filter ${filter === f.id ? 'is-active' : ''}`}
                onClick={() => { setFilter(f.id); setSel(0) }}
              >
                {f.label} <span className="corpus__filter-n mono">{counts[f.id]}</span>
              </button>
            ))}
          </div>
          <input
            className="corpus__search mono"
            placeholder="search tasks…"
            value={query}
            onChange={(e) => { setQuery(e.target.value); setSel(0) }}
          />
        </div>

        <div className="corpus__layout">
          {/* program list */}
          <div className="corpus__list panel" role="list">
            {list.length === 0 && (
              <div className="corpus__empty scrim">No programs match “{query}”.</div>
            )}
            {list.map((p, i) => {
              const isSel = active && p === active
              return (
                <button
                  key={p.task + i}
                  className={`corpus__item ${isSel ? 'is-active' : ''}`}
                  onClick={() => setSel(i)}
                  role="listitem"
                >
                  <div className="corpus__item-top">
                    <span className={`corpus__plat corpus__plat--${p.platform}`}>
                      {p.platform === 'android' ? 'phone' : 'desktop'}
                    </span>
                    <span className="corpus__item-app mono">{appLabel(p.app)}</span>
                    <span className="corpus__item-steps mono">{p.states.length} steps</span>
                  </div>
                  <div className="corpus__item-task">{p.task}</div>
                </button>
              )
            })}
          </div>

          {/* program detail */}
          <div className="corpus__detail panel">
            <AnimatePresence mode="wait">
              {active && (
                <motion.div
                  key={active.task}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -8 }}
                  transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
                >
                  <div className="corpus__detail-head">
                    <span className={`corpus__plat corpus__plat--${active.platform}`}>
                      {active.platform === 'android' ? 'phone' : 'desktop'}
                    </span>
                    <span className="mono scrim">{appLabel(active.app)}</span>
                  </div>
                  <p className="corpus__detail-task">{active.task}</p>
                  {active.params.length > 0 && (
                    <div className="corpus__params">
                      <span className="scrim mono">fill-in values:</span>
                      {active.params.map((p) => (
                        <span key={p} className="corpus__param mono">{p}</span>
                      ))}
                    </div>
                  )}

                  <div className="corpus__graph">
                    {active.states.map((st, i) => {
                      const tr = active.transitions[i]
                      const last = i === active.states.length - 1
                      return (
                        <div key={st.id + i} className="corpus__node-wrap">
                          <div className={`corpus__node ${st.verify === 'task complete' ? 'is-terminal' : ''}`}>
                            <div className="corpus__node-top">
                              <span className="corpus__node-id mono">{st.id}</span>
                              <span className="corpus__node-check">{last ? '◉' : '✓'}</span>
                            </div>
                            {st.desc && <div className="corpus__node-desc">{st.desc}</div>}
                            <div className="corpus__node-verify mono">
                              <span className="scrim">check ▸</span> {st.verify}
                            </div>
                          </div>
                          {tr && !last && (
                            <div className="corpus__edge mono">↓ {tr.action}</div>
                          )}
                        </div>
                      )
                    })}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>
      </div>
    </section>
  )
}
