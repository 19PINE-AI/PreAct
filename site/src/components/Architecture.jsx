import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import Reveal from './Reveal'
import { COMPONENTS, ALGORITHM } from '../data/architecture'
import './Architecture.css'

const toneClass = { pass: 'signal-pass', replay: 'signal-replay', amber: 'signal-amber', neutral: '' }
const toneBg = { pass: 'bg-pass', replay: 'bg-replay', amber: 'bg-amber', neutral: '' }

export default function Architecture() {
  const [sel, setSel] = useState('gate')
  const active = COMPONENTS.find((c) => c.id === sel)

  return (
    <section id="architecture">
      <div className="shell">
        <Reveal className="section-head">
          <span className="divider-num">§3 — HOW IT WORKS</span>
          <h2>Pick a program, run it, check it, save it.</h2>
          <p>
            A few simple parts share one growing library of programs. The code that runs the loop
            never changes; what grows is the library, and only programs that pass the check are
            allowed in. Tap any part to see what it does.
          </p>
        </Reveal>

        <div className="arch__layout">
          {/* interactive flow diagram */}
          <Reveal className="arch__diagram panel" delay={0.05}>
            <div className="arch__flow">
              <div className="arch__lane">
                <span className="arch__lane-tag mono">goal T</span>
                {COMPONENTS.filter((c) => ['selector', 'replayer'].includes(c.id)).map((c) => (
                  <Node key={c.id} c={c} active={sel === c.id} onClick={() => setSel(c.id)} />
                ))}
              </div>
              <div className="arch__connector" aria-hidden>
                <span className="mono arch__edge-lbl">replay fail ↓</span>
              </div>
              <div className="arch__lane">
                {COMPONENTS.filter((c) => ['cua', 'compiler'].includes(c.id)).map((c) => (
                  <Node key={c.id} c={c} active={sel === c.id} onClick={() => setSel(c.id)} />
                ))}
              </div>
              <div className="arch__connector" aria-hidden>
                <span className="mono arch__edge-lbl">P′ ↓</span>
              </div>
              <div className="arch__lane">
                {COMPONENTS.filter((c) => ['gate', 'corpus'].includes(c.id)).map((c) => (
                  <Node key={c.id} c={c} active={sel === c.id} onClick={() => setSel(c.id)} />
                ))}
              </div>
              <div className="arch__feedback mono">↺ the library is consulted again next time the task comes up</div>
            </div>
          </Reveal>

          {/* detail panel */}
          <Reveal className="arch__detail panel" delay={0.12}>
            <AnimatePresence mode="wait">
              <motion.div
                key={active.id}
                initial={{ opacity: 0, x: 14 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -10 }}
                transition={{ duration: 0.32, ease: [0.22, 1, 0.36, 1] }}
              >
                <div className="arch__detail-head">
                  <span className={`arch__detail-dot ${toneBg[active.tone]}`} />
                  <div>
                    <h3 className={toneClass[active.tone]}>{active.name}</h3>
                    <span className="arch__detail-tagline mono">{active.tagline}</span>
                  </div>
                </div>
                <p className="arch__detail-body">{active.body}</p>
                <div className="arch__detail-file mono">
                  <span className="scrim">impl ·</span> {active.file}
                </div>
              </motion.div>
            </AnimatePresence>
          </Reveal>
        </div>

        {/* algorithm */}
        <Reveal className="arch__algo" delay={0.08}>
          <div className="arch__algo-head">
            <h3>The loop, in full</h3>
            <p className="scrim">
              The only way a program ever enters the library is the gated
              <span className="mono signal-pass"> save</span> step: it must first pass an
              independent re-check, so the library can only get better, never worse.
            </p>
          </div>
          <div className="arch__code panel">
            {ALGORITHM.map((line, i) => (
              <div key={i} className={`arch__code-line arch__k-${line.kind}`}>
                <span className="arch__code-num mono">{String(i + 1).padStart(2, '0')}</span>
                <span className="arch__code-src mono">{line.l}</span>
                {line.c && <span className="arch__code-comment mono">▸ {line.c}</span>}
              </div>
            ))}
          </div>
        </Reveal>
      </div>
    </section>
  )
}

function Node({ c, active, onClick }) {
  return (
    <button className={`arch__node ${active ? 'is-active' : ''} arch__node--${c.tone}`} onClick={onClick}>
      <span className={`arch__node-dot ${toneBg[c.tone]}`} />
      <span className="arch__node-name">{c.name}</span>
      <span className="arch__node-tag mono">{c.tagline}</span>
    </button>
  )
}
