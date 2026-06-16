import { useState } from 'react'
import { motion } from 'framer-motion'
import Reveal from '../../components/Reveal'
import GateChart from './GateChart'
import {
  GATE_ANDROID, GATE_OSWORLD, MONOTONIC, BASELINES, SMOKING_GUN,
  SELECTOR_ABLATION, NEGATIVE_FINDINGS, THREATS, CROSS_MODEL,
} from '../../data/results'
import './Results.css'

export default function Results() {
  const [gateTab, setGateTab] = useState('android')
  const table = gateTab === 'android' ? GATE_ANDROID : GATE_OSWORLD

  return (
    <section id="results">
      <div className="shell">
        <Reveal className="section-head">
          <span className="divider-num">§6 — RESULTS</span>
          <h2>What we found.</h2>
          <p>
            Two findings, in plain terms. First, the re-check before saving is what makes reuse
            actually pay off. Second, most of the pieces we expected to matter did not.
          </p>
        </Reveal>

        {/* ===== 1 · why verification matters ===== */}
        <Reveal className="res__subhead">
          <span className="divider-num signal-pass">1 — WHY VERIFICATION MATTERS</span>
          <h3 className="res__subhead-h">Re-checking each program is what keeps the agent improving.</h3>
          <p>
            The same library that makes a repeated task cheap can quietly make it wrong — if it
            keeps a program that runs to the end but never actually does the job. Re-running every
            new program from a clean start, and saving it only if the task was truly solved, is what
            keeps repeated runs getting <em>better</em> instead of slowly decaying.
          </p>
        </Reveal>

        {/* ── Central figure ── */}
        <Reveal className="res__hero panel">
          <div className="res__hero-head">
            <div>
              <span className="tag"><span className="dot bg-pass" /> THE CENTRAL RESULT</span>
              <h3>The check helps by about the same amount everywhere.</h3>
              <p className="scrim">
                Change in tasks solved from a first run to a repeat, with the check
                <span className="signal-pass"> on</span> vs
                <span className="signal-fail"> off</span>, ±1σ. Across a phone, a desktop and a
                website — different models and tasks — the gap is 1.75–2.6 tasks.
              </p>
            </div>
            <div className="res__meta-stat">
              <span className="res__meta-p mono signal-pass">p ≈ 1.2×10⁻⁴</span>
              <span className="scrim">across all three benchmarks · 14 paired runs, every one favouring the check or tied</span>
            </div>
          </div>
          <GateChart />
          <div className="res__legend mono">
            <span><span className="sw bg-pass" /> with the check — repeated runs improve</span>
            <span><span className="sw bg-fail" /> without it — they get worse over time</span>
          </div>
        </Reveal>

        {/* ── per-platform tables ── */}
        <Reveal className="res__tables panel" delay={0.05}>
          <div className="res__table-tabs">
            <button className={gateTab === 'android' ? 'is-active' : ''} onClick={() => setGateTab('android')}>AndroidWorld · n=5 seeds</button>
            <button className={gateTab === 'osworld' ? 'is-active' : ''} onClick={() => setGateTab('osworld')}>OSWorld · n=5 reps</button>
          </div>
          <div className="res__table-scroll">
            <table className="res__table">
              <thead>
                <tr>{table.cols.map((c, i) => <th key={i} className={i === 0 ? 'l' : ''}>{c}</th>)}</tr>
              </thead>
              <tbody>
                {table.rows.map((r, i) => (
                  <tr key={i}>
                    {r.map((cell, j) => (
                      <td key={j} className={`${j === 0 ? 'l mono' : ''} ${typeof cell === 'string' && cell.includes('+') ? 'pos' : ''} ${typeof cell === 'string' && cell.includes('−') ? 'neg' : ''}`}>{cell}</td>
                    ))}
                  </tr>
                ))}
                <tr className="res__table-mean">
                  {table.mean.map((cell, j) => <td key={j} className={`${j === 0 ? 'l' : ''} ${typeof cell === 'string' && cell.includes('+') ? 'pos' : ''} ${typeof cell === 'string' && cell.includes('−') ? 'neg' : ''}`}>{cell}</td>)}
                </tr>
              </tbody>
            </table>
          </div>
          <p className="res__table-note scrim">{table.note}</p>
        </Reveal>

        {/* ── monotonicity + smoking gun ── */}
        <div className="res__pair">
          <Reveal className="res__card panel" delay={0.05}>
            <span className="tag"><span className="dot bg-replay" /> FIRST RUN → REPEAT</span>
            <h3>Repeated runs keep improving.</h3>
            <p className="scrim">Three independent runs, each starting from an empty library — all three improve.</p>
            <Slope data={MONOTONIC} />
            <div className="res__shifts">
              {MONOTONIC.map((m) => (
                <div key={m.seed} className="res__shift">
                  <span className="mono">seed {m.seed}</span>
                  <span className="res__shift-delta signal-pass">{m.delta}</span>
                  <span className="scrim">{m.shift}</span>
                </div>
              ))}
            </div>
          </Reveal>

          <Reveal className="res__card panel" delay={0.1}>
            <span className="tag"><span className="dot bg-fail" /> CAUGHT IN THE ACT</span>
            <h3>Programs that run, but don’t work.</h3>
            <p className="scrim">Without the check, these saved programs replay all the way through — yet the task isn’t actually done. Exactly what the check catches.</p>
            <div className="res__gun-list">
              {SMOKING_GUN.map((g) => (
                <div key={g.pid} className="res__gun">
                  <div className="res__gun-top">
                    <span className={`mono res__gun-plat res__gun-plat--${g.platform.toLowerCase()}`}>{g.platform}</span>
                    <span className="res__gun-task">{g.task}</span>
                    <span className="mono res__gun-pid">{g.pid}</span>
                  </div>
                  <p className="res__gun-mech scrim">{g.mech}</p>
                </div>
              ))}
            </div>
          </Reveal>
        </div>

        {/* ── baselines ── */}
        <Reveal className="res__card panel" delay={0.05}>
          <span className="tag"><span className="dot bg-amber" /> HEAD-TO-HEAD · WEBARENA</span>
          <h3>Matching Muscle-Mem took one more idea.</h3>
          <p className="scrim">
            Change in tasks solved from first run to repeat, on the 12-task web subset (n=4). The
            check alone trails Muscle-Mem; letting the agent explore afresh when no saved program
            fits closes the gap (statistically indistinguishable, p ≈ 0.84).
          </p>
          <div className="res__baselines">
            {BASELINES.map((b, i) => {
              const min = -7
              const pct = Math.min(100, (Math.abs(b.delta) / Math.abs(min)) * 100)
              return (
                <div key={b.sys} className={`res__baseline res__baseline--${b.kind}`}>
                  <div className="res__baseline-label">
                    <span className="res__baseline-sys">{b.sys}</span>
                    <span className="scrim">{b.subtitle}</span>
                  </div>
                  <div className="res__baseline-track">
                    <motion.div
                      className="res__baseline-bar"
                      initial={{ width: 0 }}
                      whileInView={{ width: `${pct}%` }}
                      viewport={{ once: true }}
                      transition={{ duration: 0.8, delay: i * 0.08 }}
                    />
                    <span className="res__baseline-delta mono">Δ {b.delta}</span>
                  </div>
                  <span className="res__baseline-note scrim">{b.note}</span>
                </div>
              )
            })}
          </div>
        </Reveal>

        {/* ── cross-model + threats (robustness of the same finding) ── */}
        <div className="res__pair">
          <Reveal className="res__card panel" delay={0.05}>
            <span className="tag"><span className="dot bg-pass" /> CROSS-MODEL PARITY</span>
            <h3>Same SR, same failures.</h3>
            <div className="res__xmodel">
              {[CROSS_MODEL.claude, CROSS_MODEL.gemini].map((m) => (
                <div key={m.label} className="res__xmodel-row">
                  <span>{m.label}</span>
                  <div className="res__xmodel-bar-track">
                    <motion.div className="res__xmodel-bar" initial={{ width: 0 }} whileInView={{ width: `${m.pct}%` }} viewport={{ once: true }} transition={{ duration: 0.9 }} />
                  </div>
                  <span className="mono signal-pass">{m.sr}</span>
                </div>
              ))}
            </div>
            <p className="scrim res__xmodel-note">
              Identical stable fail set across both backends and three seeds:
              {' '}<span className="mono signal-fail">{CROSS_MODEL.fails.join(' · ')}</span> — harness-deterministic UI failures, not model capability.
            </p>
          </Reveal>

          <Reveal className="res__card panel" delay={0.1}>
            <span className="tag"><span className="dot bg-pass" /> VALIDITY THREATS</span>
            <h3>11 of 11 in-scope threats closed.</h3>
            <div className="res__threats">
              {THREATS.map((t) => (
                <div key={t.n} className={`res__threat ${t.hero ? 'is-hero' : ''} ${t.oos ? 'is-oos' : ''}`} title={t.ev}>
                  <span className="res__threat-n mono">{String(t.n).padStart(2, '0')}</span>
                  <span className="res__threat-name">{t.threat}</span>
                  <span className={`res__threat-status mono ${t.oos ? 'signal-amber' : 'signal-pass'}`}>{t.oos ? '◌' : '✓'}</span>
                </div>
              ))}
            </div>
          </Reveal>
        </div>

        {/* ===== 2 · what didn't matter ===== */}
        <Reveal className="res__subhead">
          <span className="divider-num signal-fail">2 — WHAT DIDN’T MATTER</span>
          <h3 className="res__subhead-h">The pieces we expected to carry the result mostly didn’t.</h3>
          <p>
            It’s easy to credit the wrong thing. Careful prompt wording, hand-written guardrails, even
            how programs are picked from the library — each made little or no measurable difference.
            The re-check, plus falling back to the full agent when no saved program fits, are what
            actually move the numbers.
          </p>
        </Reveal>

        {/* ── selector ablation ── */}
        <Reveal className="res__card panel" delay={0.05}>
          <span className="tag"><span className="dot bg-replay" /> SELECTOR ABLATION</span>
          <h3>A tuned embedding selector matches the agentic LLM.</h3>
          <p className="scrim">Functional retrieval vs false-pick across operating points on the 58-program corpus. The hypothesis we entered with did not survive the data.</p>
          <div className="res__sel">
            <div className="res__sel-head mono">
              <span>selector</span><span>τ</span><span>functional</span><span>no-pick</span><span>false-pick</span>
            </div>
            {SELECTOR_ABLATION.map((s, i) => (
              <div key={i} className={`res__sel-row ${s.best ? 'is-best' : ''} ${s.agentic ? 'is-agentic' : ''}`}>
                <span className="res__sel-name">{s.sel}{s.best && <span className="res__sel-flag mono">optimum</span>}</span>
                <span className="mono">{s.tau}</span>
                <span className="res__sel-bar-cell">
                  <span className="res__sel-bar" style={{ width: `${s.functional}%` }} />
                  <span className="mono res__sel-num">{s.functional}%</span>
                </span>
                <span className="mono scrim">{s.nopick}</span>
                <span className={`mono ${s.falsepick > 0 ? 'signal-fail' : 'signal-pass'}`}>{s.falsepick}%</span>
              </div>
            ))}
          </div>
        </Reveal>

        {/* ── negative findings grid ── */}
        <div className="res__neg-grid">
          {NEGATIVE_FINDINGS.map((n, i) => (
            <Reveal key={n.title} className="res__neg panel" delay={i * 0.06}>
              <div className="res__neg-verdict mono">{n.verdict}</div>
              <h4>{n.title}</h4>
              <p>{n.detail}</p>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  )
}

// slope chart for cold→warm monotonicity
function Slope({ data }) {
  const W = 320, H = 150, pad = 30
  const max = 15
  const yy = (v) => H - pad - (v / max) * (H - pad * 2)
  const colors = ['var(--replay)', 'var(--pass)', 'var(--amber)']
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="res__slope">
      <text x={pad} y={H - 8} fontSize="10" fontFamily="var(--font-mono)" fill="var(--ink-mute)" textAnchor="middle">cold</text>
      <text x={W - pad} y={H - 8} fontSize="10" fontFamily="var(--font-mono)" fill="var(--ink-mute)" textAnchor="middle">warm</text>
      {[0, 5, 10, 15].map((t) => (
        <text key={t} x={10} y={yy(t) + 3} fontSize="9" fontFamily="var(--font-mono)" fill="var(--ink-mute)">{t}</text>
      ))}
      {data.map((d, i) => (
        <g key={d.seed}>
          <motion.line
            x1={pad} y1={yy(d.cold)} x2={W - pad} y2={yy(d.warm)}
            stroke={colors[i]} strokeWidth="2"
            initial={{ pathLength: 0, opacity: 0 }}
            whileInView={{ pathLength: 1, opacity: 0.9 }}
            viewport={{ once: true }}
            transition={{ duration: 1, delay: i * 0.15 }}
          />
          <circle cx={pad} cy={yy(d.cold)} r="3.5" fill={colors[i]} />
          <circle cx={W - pad} cy={yy(d.warm)} r="3.5" fill={colors[i]} />
        </g>
      ))}
    </svg>
  )
}
