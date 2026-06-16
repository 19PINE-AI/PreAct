import { useState, useEffect, useRef } from 'react'
import Reveal from '../../components/Reveal'
import PhoneFrame from '../../components/PhoneFrame'
import { EXAMPLE_PROGRAM } from '../../data/architecture'
import { TRAJECTORIES } from '../../data/trajectories'
import './Executor.css'

const P = EXAMPLE_PROGRAM
const STATES = P.states
const CONTACT = TRAJECTORIES.find((t) => t.id.startsWith('ContactsAddContact'))
const IMGS = CONTACT ? CONTACT.steps.map((s) => s.img) : []
const screenFor = (i) => IMGS[Math.min(i + 1, IMGS.length - 1)]

// Code lines of the stored program, each tagged with the op that lights it up:
// {v:i} = the verify of state i; {a:i} = the action of transition i.
const LINES = (() => {
  const out = []
  out.push({ t: 'program "add a contact"', c: 'kw' })
  out.push({ t: 'parameters: ' + P.metadata.parameters.join(', '), c: 'dim' })
  out.push({ t: '' })
  STATES.forEach((s, i) => {
    out.push({ t: `state ${s.id}`, c: 'state', v: i })
    out.push({ t: `  verify  ${s.verify}`, c: 'verify', v: i })
    const tr = P.transitions[i]
    if (tr) out.push({ t: `  do      ${tr.detail}  →  ${tr.to}`, c: 'act', a: i })
    else out.push({ t: '  done — stop here', c: 'done' })
    out.push({ t: '' })
  })
  return out
})()

// Execution: for each state, VERIFY its predicate, then DO the transition action.
const OPS = (() => {
  const o = []
  STATES.forEach((s, i) => {
    o.push({ type: 'verify', i })
    if (i < STATES.length - 1) o.push({ type: 'act', i })
  })
  return o
})()

export default function Executor() {
  const [op, setOp] = useState(0)
  const [playing, setPlaying] = useState(false)
  const timer = useRef(null)
  const codeRef = useRef(null)

  const last = OPS.length - 1
  const cur = OPS[Math.min(op, last)]
  const state = STATES[cur.i]
  const tr = P.transitions[cur.i]

  const stop = () => { clearInterval(timer.current); setPlaying(false) }
  useEffect(() => () => clearInterval(timer.current), [])
  useEffect(() => {
    const el = codeRef.current?.querySelector('.exec__line.is-active')
    if (el) el.scrollIntoView({ block: 'nearest', behavior: 'smooth' })
  }, [op])

  const play = () => {
    clearInterval(timer.current)
    let s = op >= last ? 0 : op
    setOp(s); setPlaying(true)
    timer.current = setInterval(() => {
      s += 1
      if (s > last) { clearInterval(timer.current); setPlaying(false); return }
      setOp(s)
    }, 1100)
  }
  const seek = (i) => { stop(); setOp(Math.max(0, Math.min(last, i))) }

  const active = (ln) =>
    (cur.type === 'verify' && ln.v === cur.i) || (cur.type === 'act' && ln.a === cur.i)

  return (
    <section id="executor">
      <div className="shell">
        <Reveal className="section-head">
          <span className="divider-num">§ UNDER THE HOOD — THE EXECUTOR</span>
          <h2>What a stored program looks like, and how it runs.</h2>
          <p>
            For the curious: this is the real program the agent saved for “add a contact.” To replay
            it, the agent walks the program one state at a time. At each state it first
            <strong> verifies</strong> that the screen looks the way the program expects; only if it
            matches does it <strong>do</strong> the next action and move on. Step through it.
          </p>
        </Reveal>

        <Reveal className="exec__stage" delay={0.06}>
          {/* the stored program, as code */}
          <div className="exec__code panel" ref={codeRef}>
            <div className="exec__code-head mono scrim">program ab4390a9 · stored in the library</div>
            <pre className="exec__pre">
              {LINES.map((ln, k) => (
                <div key={k} className={`exec__line ${active(ln) ? 'is-active' : ''}`}>
                  <span className="exec__ln mono">{ln.t ? String(k + 1).padStart(2, '0') : ''}</span>
                  <span className={`exec__src mono exec__src--${ln.c || 'plain'}`}>{ln.t || ' '}</span>
                </div>
              ))}
            </pre>
          </div>

          {/* the executor: what it's checking, on the real screen */}
          <div className="exec__run">
            <PhoneFrame src={screenFor(cur.i)} />
            <div className="exec__panels">
              <div className={`exec__op exec__op--${cur.type}`}>
                {cur.type === 'verify' ? (
                  <>
                    <span className="exec__op-tag mono">VERIFY</span>
                    <div className="exec__op-body">
                      <span className="exec__op-state mono">state {state.id}</span>
                      <div className="exec__op-expect">
                        expects: <strong>{state.verify}</strong>
                      </div>
                      <div className="exec__op-result signal-pass">✓ the screen matches</div>
                    </div>
                  </>
                ) : (
                  <>
                    <span className="exec__op-tag exec__op-tag--act mono">DO</span>
                    <div className="exec__op-body">
                      <div className="exec__op-expect"><strong>{tr.detail}</strong></div>
                      <div className="exec__op-result signal-replay">→ then move to {tr.to}</div>
                    </div>
                  </>
                )}
              </div>

              <div className="exec__controls">
                <button className="exec__ctrl" onClick={() => seek(op - 1)} disabled={op === 0}>‹ step</button>
                <button className="btn btn-primary" onClick={playing ? stop : play}>
                  {playing ? '⏸ pause' : op >= last ? '↻ run again' : '▶ run'}
                </button>
                <button className="exec__ctrl" onClick={() => seek(op + 1)} disabled={op >= last}>step ›</button>
              </div>
              <div className="exec__progress mono scrim">
                op {Math.min(op, last) + 1} / {OPS.length} · verify → do → verify → do …
              </div>
            </div>
          </div>
        </Reveal>
      </div>
    </section>
  )
}
