import Reveal from '../../components/Reveal'
import './Problem.css'

const RELATED = [
  { sys: 'Skill libraries (e.g. Voyager)', mem: 'Code skills run by an LLM', fallback: 'The agent', ext: 'Grows & self-checks a library' },
  { sys: 'Muscle-Mem', mem: 'A recorded list of actions', fallback: 'The agent on a miss', ext: 'Append only' },
  { sys: 'Workflow-Use', mem: 'Per-task scripts', fallback: 'The agent', ext: 'Append only' },
  { sys: 'ActionEngine', mem: 'A program built by crawling', fallback: 'None', ext: 'Re-crawl from scratch' },
  { sys: 'PreAct', mem: 'A program the agent runs directly', fallback: 'The agent, then re-compile & check', ext: 'Refines & re-checks what it keeps', hero: true },
]

export default function Problem() {
  return (
    <section id="problem">
      <div className="shell">
        <Reveal className="section-head">
          <span className="divider-num">§1 — THE PROBLEM</span>
          <h2>Agents re-solve tasks they have already solved.</h2>
          <p>
            A computer-using agent works out every task from the screen, step by step. Run
            “add a contact” on Monday and again on Tuesday and it does all the same reading and
            reasoning both days — even though the screen and the taps are identical.
          </p>
        </Reveal>

        <div className="problem__grid">
          <Reveal className="problem__card problem__card--fail" delay={0.05}>
            <span className="tag"><span className="dot bg-fail" /> Plain agent</span>
            <div className="problem__cost mono">full cost</div>
            <p className="problem__cost-cap">
              Every run pays for fresh screen-reading and reasoning at each step —
              even for a task the agent has already done.
            </p>
            <div className="problem__bars">
              {[1, 2, 3, 4, 5].map((d) => (
                <div key={d} className="problem__run">
                  <span className="mono problem__run-lbl">run {d}</span>
                  <div className="problem__bar problem__bar--full" />
                  <span className="mono signal-fail">full cost</span>
                </div>
              ))}
            </div>
          </Reveal>

          <Reveal className="problem__card problem__card--pass" delay={0.12}>
            <span className="tag"><span className="dot bg-pass" /> PreAct</span>
            <div className="problem__cost mono signal-pass">≈ free after run 1</div>
            <p className="problem__cost-cap">
              The first success becomes a small program. Later runs <em>replay</em> it —
              no model calls until the screen actually changes.
            </p>
            <div className="problem__bars">
              {[
                { d: 1, full: true, lbl: 'compile', tone: 'amber' },
                { d: 2, full: false, lbl: 'replay', tone: 'pass' },
                { d: 3, full: false, lbl: 'replay', tone: 'pass' },
                { d: 4, full: false, lbl: 'replay', tone: 'pass' },
                { d: 5, full: false, lbl: 'replay', tone: 'pass' },
              ].map((r) => (
                <div key={r.d} className="problem__run">
                  <span className="mono problem__run-lbl">run {r.d}</span>
                  <div className={`problem__bar ${r.full ? 'problem__bar--full-amber' : 'problem__bar--thin'}`} />
                  <span className={`mono signal-${r.tone}`}>{r.lbl}</span>
                </div>
              ))}
            </div>
          </Reveal>
        </div>

        <Reveal className="problem__related panel" delay={0.1}>
          <div className="problem__related-head">
            <h3>Where PreAct sits</h3>
            <p className="scrim">
              Others either keep a model in the loop when they reuse, or store something they
              cannot reliably re-run. PreAct stores a program it runs directly, and re-checks it
              before keeping it.
            </p>
          </div>
          <div className="problem__table" role="table">
            <div className="problem__row problem__row--head" role="row">
              <span>System</span><span>Memory representation</span><span>Fallback path</span><span>Self-extension</span>
            </div>
            {RELATED.map((r) => (
              <div key={r.sys} className={`problem__row ${r.hero ? 'problem__row--hero' : ''}`} role="row">
                <span className="problem__sys">{r.sys}</span>
                <span>{r.mem}</span>
                <span>{r.fallback}</span>
                <span>{r.ext}</span>
              </div>
            ))}
          </div>
        </Reveal>
      </div>
    </section>
  )
}
