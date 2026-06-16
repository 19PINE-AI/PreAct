import { useState, useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import Reveal from './Reveal'
import { EXAMPLE_PROGRAM } from '../data/architecture'
import './Demo.css'

// Three scenarios the harness can encounter on a compiled program.
const SCENARIOS = {
  faithful: {
    label: 'It works',
    tone: 'pass',
    blurb: 'Every check matches the live screen, the program runs to the end, and the evaluator confirms the contact was actually created.',
    failAt: -1,
    cov: 100,
    score: 1.0,
    verdict: 'SAVED',
    verdictNote: 'It ran to the end and the task was really solved — so the program is saved.',
  },
  lossy: {
    label: 'Runs, but does not actually work',
    tone: 'fail',
    blurb: 'The program runs all the way to its last step, but the contact was never created — the dangerous case. This is exactly what the check is for.',
    failAt: -1,
    cov: 100,
    score: 0.0,
    verdict: 'REJECTED',
    verdictNote: 'It reached the end, but the task was not solved — so the program is thrown away, not saved.',
  },
  replayfail: {
    label: 'A check fails → hand off to the agent',
    tone: 'amber',
    blurb: 'Partway through, the screen no longer looks the way the program expects. It stops there and hands the task to the full agent.',
    failAt: 2,
    cov: 40,
    score: null,
    verdict: 'HANDED OFF',
    verdictNote: 'A check failed partway through, so the full agent takes over and finishes the task.',
  },
}

export default function Demo() {
  const [scenario, setScenario] = useState('faithful')
  const [step, setStep] = useState(0) // 0 = idle, 1..N states verified, N+1 = verdict
  const [running, setRunning] = useState(false)
  const timer = useRef(null)
  const sc = SCENARIOS[scenario]
  const states = EXAMPLE_PROGRAM.states
  const total = states.length

  const reset = () => {
    clearTimeout(timer.current)
    setStep(0)
    setRunning(false)
  }
  useEffect(() => reset(), [scenario])
  useEffect(() => () => clearTimeout(timer.current), [])

  const run = () => {
    reset()
    setRunning(true)
    let s = 0
    const advance = () => {
      s += 1
      setStep(s)
      const haltState = sc.failAt >= 0 ? sc.failAt + 1 : total
      if (s >= haltState) {
        timer.current = setTimeout(() => {
          setStep(haltState + 1) // verdict
          setRunning(false)
        }, 700)
        return
      }
      timer.current = setTimeout(advance, 780)
    }
    timer.current = setTimeout(advance, 400)
  }

  const haltState = sc.failAt >= 0 ? sc.failAt + 1 : total
  const showVerdict = step > haltState

  return (
    <section id="demo">
      <div className="shell">
        <Reveal className="section-head">
          <span className="divider-num">§ INTERACTIVE — TRY IT</span>
          <h2>Run a real program, step by step.</h2>
          <p>
            This is an actual saved program for the “add a contact” task. Choose what happens when
            it runs, press replay, and watch how the check decides whether the program is good
            enough to keep.
          </p>
        </Reveal>

        <div className="demo__controls">
          {Object.entries(SCENARIOS).map(([k, v]) => (
            <button
              key={k}
              className={`demo__scenario ${scenario === k ? 'is-active' : ''} demo__scenario--${v.tone}`}
              onClick={() => setScenario(k)}
            >
              <span className={`dot bg-${v.tone}`} />
              {v.label}
            </button>
          ))}
        </div>

        <div className="demo__stage">
          {/* state machine */}
          <div className="demo__machine panel">
            <div className="demo__machine-head">
              <span className="mono scrim">PROGRAM · add a contact (ab4390a9)</span>
              <button className="btn btn-primary demo__run" onClick={run} disabled={running}>
                {running ? 'replaying…' : '▶ replay program'}
              </button>
            </div>

            <div className="demo__states">
              {states.map((st, i) => {
                const reached = step > i
                const isFailPoint = sc.failAt === i && step >= i + 1
                const verified = reached && !isFailPoint
                const current = step === i + 1 && running
                const trans = EXAMPLE_PROGRAM.transitions[i]
                return (
                  <div key={st.id} className="demo__state-wrap">
                    <motion.div
                      className={`demo__state ${verified ? 'is-verified' : ''} ${isFailPoint ? 'is-failed' : ''} ${current ? 'is-current' : ''} ${st.terminal ? 'is-terminal' : ''}`}
                      animate={current ? { scale: [1, 1.03, 1] } : {}}
                      transition={{ duration: 0.5 }}
                    >
                      <div className="demo__state-top">
                        <span className="demo__state-id mono">{st.id}</span>
                        <span className="demo__state-check">
                          {isFailPoint ? '✕' : verified ? '✓' : st.terminal ? '◉' : '○'}
                        </span>
                      </div>
                      <div className="demo__state-desc">{st.desc}</div>
                      <div className="demo__state-verify mono">{st.verify}</div>
                    </motion.div>
                    {trans && i < states.length - 1 && (
                      <div className={`demo__edge ${step > i + 1 ? 'is-lit' : ''}`}>
                        <span className="demo__edge-action mono">{trans.action}</span>
                        <span className="demo__edge-detail">{trans.detail}</span>
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          </div>

          {/* gate / verdict console */}
          <div className="demo__console panel">
            <span className="mono scrim">THE CHECK</span>
            <p className="demo__blurb">{sc.blurb}</p>

            <div className="demo__meters">
              <Meter label="steps completed" value={showVerdict ? sc.cov : step > 0 ? Math.round((Math.min(step, haltState) / total) * 100) : 0} suffix="%" tone={sc.tone} />
              <div className="demo__meter">
                <span className="mono demo__meter-lbl">task actually solved?</span>
                <span className={`demo__score mono ${showVerdict && sc.score !== null ? (sc.score >= 1 ? 'signal-pass' : 'signal-fail') : 'scrim'}`}>
                  {showVerdict && sc.score !== null ? sc.score.toFixed(1) : '—'}
                </span>
              </div>
            </div>

            <AnimatePresence>
              {showVerdict && (
                <motion.div
                  className={`demo__verdict demo__verdict--${sc.tone}`}
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.4 }}
                >
                  <div className="demo__verdict-tag mono">{sc.verdict}</div>
                  <p>{sc.verdictNote}</p>
                </motion.div>
              )}
            </AnimatePresence>

            {!showVerdict && (
              <div className="demo__idle scrim mono">
                {running ? '› running the program…' : '› press replay to see what the check decides'}
              </div>
            )}
          </div>
        </div>
      </div>
    </section>
  )
}

function Meter({ label, value, suffix, tone }) {
  return (
    <div className="demo__meter">
      <span className="mono demo__meter-lbl">{label}</span>
      <div className="demo__meter-bar">
        <motion.div
          className={`demo__meter-fill bg-${tone}`}
          animate={{ width: `${value}%` }}
          transition={{ duration: 0.5 }}
        />
      </div>
      <span className={`mono demo__meter-val signal-${tone}`}>{value}{suffix}</span>
    </div>
  )
}
