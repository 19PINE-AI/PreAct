import { useState, useEffect, useRef, useMemo } from 'react'
import Reveal from '../../components/Reveal'
import { PROGRAMS } from '../../data/programs'
import './Trajectories.css'

const BASE = import.meta.env.BASE_URL || '/'

// Order: the two environments with real screenshots first, the accessibility-tree
// one (OSWorld, no screenshots recorded) last.
const PLATFORMS = [
  {
    key: 'android', label: 'Android', sub: 'AndroidWorld', frame: 'phone',
    note: 'The real phone screenshots from the agent’s run appear on the right.',
  },
  {
    key: 'web', label: 'Browser', sub: 'WebArena', frame: 'browser',
    note: 'The real browser screenshots from the agent’s run appear on the right.',
  },
  {
    key: 'desktop', label: 'Desktop', sub: 'OSWorld', frame: 'window',
    note: 'OSWorld verifies against the desktop accessibility tree — no screenshots were recorded — so we render the verified screen state instead.',
  },
]

// Unroll a compiled program into a linear verify→do→verify walk and the matching
// lines of "source". Transitions are followed by from-state id, first match wins.
function compile(p) {
  const states = p.states
  const txByFrom = {}
  p.transitions.forEach((t) => {
    if (!(t.from in txByFrom)) txByFrom[t.from] = t
  })

  const ops = []
  const lines = []
  lines.push({ t: `program ${JSON.stringify(p.name)}`, c: 'kw' })
  lines.push({ t: `context  ${p.app}`, c: 'dim' })
  if (p.params && p.params.length) lines.push({ t: `params   ${p.params.map((x) => '$' + x).join(', ')}`, c: 'dim' })
  lines.push({ t: '' })

  states.forEach((s, i) => {
    const tr = txByFrom[s.id]
    const terminal = !tr
    lines.push({ t: `state ${s.id}`, c: 'state', v: i })
    lines.push({ t: `  verify  ${s.verify}`, c: 'verify', v: i })
    ops.push({ type: 'verify', i, terminal })
    if (!terminal) {
      lines.push({ t: `  do      ${tr.action}  →  ${tr.to}`, c: 'act', a: i })
      ops.push({ type: 'act', i, tr })
    } else {
      lines.push({ t: '  done — stop here', c: 'done' })
    }
    lines.push({ t: '' })
  })
  return { ops, lines, txByFrom }
}

export default function Trajectories() {
  return (
    <section id="programs">
      <div className="shell">
        <Reveal className="section-head">
          <span className="divider-num">§ THE PROGRAMS — WATCH ONE RUN</span>
          <h2>What the agent learns, and how it runs.</h2>
          <p>
            The first time the agent finishes a task, it compiles the run into a small program:
            <em> states</em>, each with a check on the screen, joined by <em>transitions</em>, each with
            one action. To reuse it, the executor walks the program — at every state it first
            <strong> verifies</strong> the screen looks the way the program expects, and only then
            <strong> does</strong> the next action. No model is involved, so a clean replay is fast and
            cheap. The same program format runs across all three environments below — pick a task in any
            of them and step through its real compiled program.
          </p>
        </Reveal>

        {PLATFORMS.map((pf, i) => (
          <ProgramPlayer
            key={pf.key}
            platform={pf.key}
            label={pf.label}
            sub={pf.sub}
            frame={pf.frame}
            note={pf.note}
            delay={0.04 + i * 0.02}
          />
        ))}

        <p className="pg__foot scrim">
          Every program is the real state machine PreAct compiled from a successful benchmark run —
          verification predicates and actions shown verbatim.
        </p>
      </div>
    </section>
  )
}

// One self-contained simulator for a single environment: task picker + run bar +
// the compiled program (left) running against the real screen (right).
function ProgramPlayer({ platform, label, sub, frame, note, delay = 0 }) {
  const list = PROGRAMS[platform]
  const [sel, setSel] = useState(0)
  const [op, setOp] = useState(0)
  const [playing, setPlaying] = useState(false)
  const timer = useRef(null)
  const codeRef = useRef(null)

  const prog = list[Math.min(sel, list.length - 1)]
  const { ops, lines } = useMemo(() => compile(prog), [prog])
  const last = ops.length - 1
  const cur = ops[Math.min(op, last)]
  const state = prog.states[cur.i]

  const screens = prog.screens || []
  const M = screens.length
  const frac = last > 0 ? Math.min(op, last) / last : 0
  const shotIdx = M ? Math.round(frac * (M - 1)) : -1
  const shot = M ? BASE + screens[shotIdx] : null

  const stop = () => { clearInterval(timer.current); setPlaying(false) }
  useEffect(() => { stop(); setOp(0) }, [sel])
  useEffect(() => () => clearInterval(timer.current), [])
  useEffect(() => {
    const el = codeRef.current?.querySelector('.pg__line.is-active')
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
    }, 1050)
  }
  const seek = (i) => { stop(); setOp(Math.max(0, Math.min(last, i))) }
  const active = (ln) =>
    (cur.type === 'verify' && ln.v === cur.i) || (cur.type === 'act' && ln.a === cur.i)

  return (
    <Reveal className="pg__sub" delay={delay}>
      <div className="pg__sub-head">
        <h3 className="pg__sub-title">{label}</h3>
        <span className="pg__sub-env mono">{sub}</span>
        <p className="pg__sub-note">{note}</p>
      </div>

      <div className="pg__tasks">
        {list.map((t, i) => (
          <button
            key={t.id}
            className={`pg__task ${i === sel ? 'is-active' : ''}`}
            onClick={() => setSel(i)}
          >
            {t.name}
          </button>
        ))}
      </div>

      <div className="pg__runbar">
        <button className="btn btn-primary pg__runbtn" onClick={playing ? stop : play}>
          {playing ? '⏸ pause' : op >= last ? '↻ run again' : '▶ run program'}
        </button>
        <div className="pg__stepper">
          <button className="pg__ctrl" onClick={() => seek(op - 1)} disabled={op === 0}>‹ step</button>
          <span className="pg__stepper-pos mono">op {Math.min(op, last) + 1} / {ops.length}</span>
          <button className="pg__ctrl" onClick={() => seek(op + 1)} disabled={op >= last}>step ›</button>
        </div>
        <span className="pg__flow mono scrim">verify → do → verify → do …</span>
      </div>

      <div className="pg__stage">
        {/* left — the compiled program + the operation running right now */}
        <div className="pg__left">
          <div className="pg__code panel" ref={codeRef}>
            <div className="pg__code-head mono scrim">
              <span>compiled program · {sub}</span>
              <span className="pg__code-task">{prog.task}</span>
            </div>
            <pre className="pg__pre">
              {lines.map((ln, k) => (
                <div key={k} className={`pg__line ${active(ln) ? 'is-active' : ''}`}>
                  <span className="pg__ln mono">{ln.t ? String(k + 1).padStart(2, '0') : ''}</span>
                  <span className={`pg__src mono pg__src--${ln.c || 'plain'}`}>{ln.t || ' '}</span>
                </div>
              ))}
            </pre>
          </div>

          <div className={`pg__op pg__op--${cur.type}`}>
            {cur.type === 'verify' ? (
              <>
                <span className="pg__op-tag mono">VERIFY</span>
                <div className="pg__op-body">
                  <span className="pg__op-state mono">state {state.id}</span>
                  <div className="pg__op-expect">
                    expects <strong>{state.verify}</strong>
                  </div>
                  <div className="pg__op-result signal-pass">
                    {cur.terminal ? '✓ goal reached' : '✓ the screen matches'}
                  </div>
                </div>
              </>
            ) : (
              <>
                <span className="pg__op-tag pg__op-tag--act mono">DO</span>
                <div className="pg__op-body">
                  <span className="pg__op-state mono">state {state.id}</span>
                  <div className="pg__op-expect"><strong>{cur.tr.action}</strong></div>
                  <div className="pg__op-result signal-replay">→ then move to {cur.tr.to}</div>
                </div>
              </>
            )}
          </div>
        </div>

        {/* right — the real screen where we have it */}
        <div className={`pg__screen pg__screen--${frame}`}>
          <Screen frame={frame} src={shot} state={state} app={prog.app} />
        </div>
      </div>
    </Reveal>
  )
}

// The screen panel: a phone bezel (Android), a browser chrome (Web), or a desktop
// window whose body shows the verified state (OSWorld — no screenshot was recorded).
function Screen({ frame, src, state, app }) {
  if (frame === 'phone') {
    return (
      <div className="pg__phone">
        <div className="pg__phone-bezel">
          <span className="pg__phone-cam" />
          <div className="pg__phone-screen">
            {src ? <img src={src} alt="" loading="lazy" /> : <div className="pg__blank" />}
          </div>
        </div>
      </div>
    )
  }
  if (frame === 'browser') {
    return (
      <div className="pg__browser">
        <div className="pg__browser-bar">
          <span className="pg__dot" /><span className="pg__dot" /><span className="pg__dot" />
          <span className="pg__url mono">{app}</span>
        </div>
        <div className="pg__browser-screen">
          {src ? <img src={src} alt="" loading="lazy" /> : <div className="pg__blank" />}
        </div>
      </div>
    )
  }
  // desktop window — no screenshot, render the verified a11y state
  return (
    <div className="pg__window">
      <div className="pg__window-bar">
        <span className="pg__dot pg__dot--r" /><span className="pg__dot pg__dot--y" /><span className="pg__dot pg__dot--g" />
        <span className="pg__window-title mono">{app}</span>
      </div>
      <div className="pg__window-body">
        <span className="pg__window-lbl mono scrim">SCREEN STATE</span>
        <p className="pg__window-desc">{state.desc}</p>
        <div className="pg__window-pred mono">
          <span className="signal-pass">✓</span> {state.verify}
        </div>
        <span className="pg__window-note scrim">accessibility tree · no screenshot recorded</span>
      </div>
    </div>
  )
}
