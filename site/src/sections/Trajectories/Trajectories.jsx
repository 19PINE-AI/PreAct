import { useState, useEffect, useRef } from 'react'
import Reveal from '../../components/Reveal'
import PhoneFrame from '../../components/PhoneFrame'
import { TRAJECTORIES } from '../../data/trajectories'
import './Trajectories.css'

// Merged "Programs the agent learned" + real-run replay: on the left, the saved
// program runs step by step; on the right, the real phone screen it produced.
export default function Trajectories() {
  const [sel, setSel] = useState(0)
  const [step, setStep] = useState(0)
  const [playing, setPlaying] = useState(false)
  const timer = useRef(null)
  const stepsRef = useRef(null)

  const task = TRAJECTORIES[sel]
  const steps = task.steps
  const last = steps.length - 1
  const cur = steps[Math.min(step, last)]

  const stop = () => { clearInterval(timer.current); setPlaying(false) }
  useEffect(() => { stop(); setStep(0) }, [sel])
  useEffect(() => () => clearInterval(timer.current), [])

  // keep the active step scrolled into view in the (scrollable) program list
  useEffect(() => {
    const el = stepsRef.current?.querySelector('.prog__step.is-cur')
    if (el) el.scrollIntoView({ block: 'nearest', behavior: 'smooth' })
  }, [step])

  const play = () => {
    clearInterval(timer.current)
    let s = step >= last ? 0 : step
    setStep(s); setPlaying(true)
    timer.current = setInterval(() => {
      s += 1
      if (s > last) { clearInterval(timer.current); setPlaying(false); return }
      setStep(s)
    }, 1000)
  }
  const seek = (i) => { stop(); setStep(Math.max(0, Math.min(last, i))) }

  return (
    <section id="programs">
      <div className="shell">
        <Reveal className="section-head">
          <span className="divider-num">§ THE PROGRAMS — WATCH ONE RUN</span>
          <h2>What the agent learns, and how it replays.</h2>
          <p>
            The first time the agent finishes a task, it saves the run as a small program it can
            replay. Pick a task below: the program runs step by step on the left, and the real
            phone screen it produced appears on the right. Press replay, or click any step.
          </p>
        </Reveal>

        <Reveal className="prog__tasks" delay={0.05}>
          {TRAJECTORIES.map((t, i) => (
            <button
              key={t.id}
              className={`prog__task ${i === sel ? 'is-active' : ''}`}
              onClick={() => setSel(i)}
            >
              {t.name}
            </button>
          ))}
        </Reveal>

        <Reveal className="prog__stage" delay={0.08}>
          {/* left — the program, executing */}
          <div className="prog__panel panel">
            <div className="prog__panel-head">
              <span className="mono scrim">PROGRAM · {task.name}</span>
              <button className="btn btn-primary prog__run" onClick={playing ? stop : play}>
                {playing ? '⏸ pause' : step >= last ? '↻ replay' : '▶ replay'}
              </button>
            </div>
            <p className="prog__goal">{task.goal}</p>
            <div className="prog__steps" ref={stepsRef}>
              {steps.map((s, i) => {
                const done = i < step
                const isCur = i === step
                const terminal = i === last
                return (
                  <button
                    key={i}
                    className={`prog__step ${done ? 'is-done' : ''} ${isCur ? 'is-cur' : ''}`}
                    onClick={() => seek(i)}
                  >
                    <span className="prog__step-tick">
                      {done ? '✓' : isCur ? '▸' : terminal ? '◉' : '○'}
                    </span>
                    <span className="prog__step-act">
                      {s.action && s.action !== 'done'
                        ? s.action
                        : <span className="signal-pass">task complete</span>}
                    </span>
                    <span className="prog__step-n mono">{s.n}</span>
                  </button>
                )
              })}
            </div>
          </div>

          {/* right — the real screen */}
          <div className="prog__screen">
            <PhoneFrame src={cur.img} />
            <div className="prog__screen-meta">
              <span className="mono scrim">step {cur.n} / {steps[last].n}</span>
              <div className="prog__nav">
                <button className="prog__ctrl" onClick={() => seek(step - 1)} disabled={step === 0}>‹</button>
                <span className="prog__nav-action">
                  {cur.action && cur.action !== 'done' ? cur.action : '✓ done'}
                </span>
                <button className="prog__ctrl" onClick={() => seek(step + 1)} disabled={step >= last}>›</button>
              </div>
            </div>
          </div>
        </Reveal>

        <p className="prog__foot scrim">
          Real screenshots captured while the agent ran each task on the AndroidWorld benchmark.
        </p>
      </div>
    </section>
  )
}
