import Reveal from './Reveal'
import { MODULES, ACTION_SCHEMA, ENV_KNOBS, EXAMPLE_PROGRAM } from '../data/architecture'
import './Implementation.css'

export default function Implementation() {
  const totalLines = MODULES.reduce((a, m) => a + m.lines, 0)
  return (
    <section id="implementation">
      <div className="shell">
        <Reveal className="section-head">
          <span className="divider-num">§4 — UNDER THE HOOD</span>
          <h2>A handful of packages, one growing library.</h2>
          <p>
            The loop lives across a few small packages, and every program is just plain JSON —
            states and the actions between them. Each result in the paper can be reproduced by
            flipping one setting.
          </p>
        </Reveal>

        <div className="impl__top">
          {/* module map */}
          <Reveal className="impl__modules" delay={0.05}>
            <div className="impl__modules-head">
              <h3>Where the code lives</h3>
              <span className="mono scrim">{totalLines.toLocaleString()} lines across the project</span>
            </div>
            <div className="impl__module-list">
              {MODULES.map((m) => {
                const pct = Math.round((m.lines / 5888) * 100)
                return (
                  <div key={m.name} className="impl__module">
                    <div className="impl__module-row">
                      <span className="impl__module-name mono">{m.name}</span>
                      <span className="impl__module-comp">{m.comp}</span>
                      <span className="impl__module-loc mono">{m.lines.toLocaleString()}</span>
                    </div>
                    <p className="impl__module-role">{m.role}</p>
                    <div className="impl__module-track">
                      <div className="impl__module-bar" style={{ width: `${Math.max(pct, 6)}%` }} />
                    </div>
                  </div>
                )
              })}
            </div>
          </Reveal>

          {/* program JSON */}
          <Reveal className="impl__program panel" delay={0.12}>
            <div className="impl__program-head">
              <span className="mono scrim">saved program · add a contact</span>
              <span className="tag"><span className="dot bg-pass" /> runs directly — no model in the loop</span>
            </div>
            <pre className="impl__json mono">
              <Json data={EXAMPLE_PROGRAM} />
            </pre>
          </Reveal>
        </div>

        <div className="impl__bottom">
          <Reveal className="impl__schema panel" delay={0.06}>
            <h3>Computer-action schema</h3>
            <p className="scrim">Each transition uses exactly one type, translated to a platform backend at execution.</p>
            <div className="impl__schema-grid">
              {ACTION_SCHEMA.map(([t, d]) => (
                <div key={t} className="impl__action">
                  <span className="impl__action-t mono">{t}</span>
                  <span className="impl__action-d">{d}</span>
                </div>
              ))}
            </div>
          </Reveal>

          <Reveal className="impl__knobs panel" delay={0.1}>
            <h3>Settings you can flip</h3>
            <p className="scrim">Each experiment in the paper is one setting away from reproducible.</p>
            <div className="impl__knob-list">
              {ENV_KNOBS.map((k) => (
                <div key={k.k} className="impl__knob">
                  <div className="impl__knob-row">
                    <span className="impl__knob-k mono">{k.k}</span>
                    <span className="impl__knob-v mono">{k.v}</span>
                  </div>
                  <p>{k.d}</p>
                </div>
              ))}
            </div>
          </Reveal>
        </div>
      </div>
    </section>
  )
}

// Tiny syntax-highlighting JSON renderer for the program example.
function Json({ data }) {
  return (
    <>
      <Line t="{" d={0} />
      <Block label="metadata" depth={1}>
        <KV k="task_description" v={`"${data.metadata.task_description}"`} />
        <KV k="application_context" v={`"${data.metadata.application_context}"`} />
        <KV k="parameters" v={`[${data.metadata.parameters.map((p) => `"${p}"`).join(', ')}]`} arr last />
      </Block>
      <Line t='"states": [' d={1} />
      {data.states.map((s, i) => (
        <Line key={s.id} d={2} t={`{ id: "${s.id}", verify: "${s.verify}" }${i < data.states.length - 1 ? ',' : ''}`} state />
      ))}
      <Line t="]," d={1} />
      <Line t='"transitions": [' d={1} />
      {data.transitions.map((t, i) => (
        <Line key={i} d={2} t={`{ ${t.from} → ${t.to} · ${t.action} }${i < data.transitions.length - 1 ? ',' : ''}`} trans />
      ))}
      <Line t="]" d={1} />
      <Line t="}" d={0} />
    </>
  )
}
function Line({ t, d = 0, state, trans }) {
  const cls = state ? 'j-state' : trans ? 'j-trans' : 'j-brace'
  return <div className={`impl__json-line ${cls}`} style={{ paddingLeft: `${d * 16}px` }}>{t}</div>
}
function Block({ label, depth, children }) {
  return (
    <>
      <Line t={`"${label}": {`} d={depth} />
      <div style={{ paddingLeft: `${(depth + 1) * 16}px` }}>{children}</div>
      <Line t="}," d={depth} />
    </>
  )
}
function KV({ k, v, arr, last }) {
  return (
    <div className="impl__json-line">
      <span className="j-key">"{k}"</span>: <span className={arr ? 'j-arr' : 'j-val'}>{v}</span>{!last && ','}
    </div>
  )
}
