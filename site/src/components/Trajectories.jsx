import { useState, useEffect, useRef } from 'react'
import Reveal from './Reveal'
import PhoneFrame from './PhoneFrame'
import { TRAJECTORIES } from '../data/trajectories'
import './Trajectories.css'

export default function Trajectories() {
  const [sel, setSel] = useState(0)
  const [step, setStep] = useState(0)
  const [playing, setPlaying] = useState(false)
  const timer = useRef(null)

  const task = TRAJECTORIES[sel]
  const steps = task.steps
  const cur = steps[Math.min(step, steps.length - 1)]

  const stop = () => { clearInterval(timer.current); setPlaying(false) }
  useEffect(() => { stop(); setStep(0) }, [sel])
  useEffect(() => () => clearInterval(timer.current), [])

  const play = () => {
    clearInterval(timer.current)
    let s = step >= steps.length - 1 ? 0 : step
    setStep(s); setPlaying(true)
    timer.current = setInterval(() => {
      s += 1
      if (s >= steps.length) { clearInterval(timer.current); setPlaying(false); return }
      setStep(s)
    }, 950)
  }
  const go = (d) => { stop(); setStep((s) => Math.max(0, Math.min(steps.length - 1, s + d))) }

  return (
    <section id="trajectories">
      <div className="shell">
        <Reveal className="section-head">
          <span className="divider-num">§ WATCH — REAL RUNS</span>
          <h2>Replay an actual run, screen by screen.</h2>
          <p>
            These are real screenshots captured while the agent solved tasks on a phone
            (the AndroidWorld benchmark). Pick a task and press replay to watch the agent
            move through the app, one screen and one action at a time.
          </p>
        </Reveal>

        <div className="traj__layout">
          {/* task list */}
          <div className="traj__list panel">
            {TRAJECTORIES.map((t, i) => (
              <button
                key={t.id}
                className={`traj__item ${i === sel ? 'is-active' : ''}`}
                onClick={() => setSel(i)}
              >
                <span className="traj__item-name">{t.name}</span>
                <span className="traj__item-steps mono">{t.steps.length}</span>
              </button>
            ))}
          </div>

          {/* player */}
          <div className="traj__player panel">
            <p className="traj__goal"><span className="scrim mono">task ·</span> {task.goal}</p>

            <div className="traj__stage">
              <PhoneFrame src={cur.img} />
              <div className="traj__side">
                <div className="traj__stepnum mono">step {cur.n} / {steps[steps.length - 1].n}</div>
                <div className="traj__action">
                  {cur.action && cur.action !== 'done'
                    ? <><span className="scrim">agent does:</span> <strong>{cur.action}</strong></>
                    : <span className="signal-pass">✓ task complete</span>}
                </div>
                <div className="traj__dots">
                  {steps.map((s, i) => (
                    <button
                      key={i}
                      className={`traj__dot ${i === step ? 'is-on' : ''} ${i < step ? 'is-done' : ''}`}
                      onClick={() => { stop(); setStep(i) }}
                      aria-label={`step ${s.n}`}
                    />
                  ))}
                </div>
                <div className="traj__controls">
                  <button className="traj__ctrl" onClick={() => go(-1)} disabled={step === 0}>‹ prev</button>
                  <button className="btn btn-primary traj__play" onClick={playing ? stop : play}>
                    {playing ? '⏸ pause' : step >= steps.length - 1 ? '↻ replay' : '▶ replay'}
                  </button>
                  <button className="traj__ctrl" onClick={() => go(1)} disabled={step >= steps.length - 1}>next ›</button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
