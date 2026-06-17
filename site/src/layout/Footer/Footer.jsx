import Reveal from '../../components/Reveal'
import './Footer.css'

export default function Footer() {
  return (
    <footer className="footer" id="cite">
      <div className="shell">
        <Reveal className="footer__cta panel">
          <div>
            <span className="divider-num">OPEN SOURCE</span>
            <h2>Open, and reproducible.</h2>
            <p>
              The code, the run scripts, and the saved programs from every run are released.
              Each experiment in the paper can be reproduced by flipping a single setting.
            </p>
            <div className="footer__links">
              <a className="btn btn-primary" href="https://arxiv.org/abs/2606.17929" target="_blank" rel="noreferrer">arXiv:2606.17929 ↗</a>
              <a className="btn" href="https://github.com/19PINE-AI/PreAct" target="_blank" rel="noreferrer">github.com/19PINE-AI/PreAct ↗</a>
              <a className="btn" href="https://01.me/research/PreAct/" target="_blank" rel="noreferrer">01.me/research/PreAct ↗</a>
            </div>
          </div>
          <div className="footer__repro mono">
            <div className="footer__repro-row"><span className="scrim"># verify-before-store ablation</span></div>
            <div className="footer__repro-row">python -m benchmark.androidworld.run_docker \</div>
            <div className="footer__repro-row footer__indent">--tasks $OFFICIAL_15 --seed 42 \</div>
            <div className="footer__repro-row footer__indent"><span className="signal-pass">--no-verify-before-store</span>  <span className="scrim"># gate off</span></div>
            <div className="footer__repro-row footer__spacer"> </div>
            <div className="footer__repro-row"><span className="scrim"># WebArena gate: PREACT_VERIFY_BEFORE_STORE=off</span></div>
            <div className="footer__repro-row"><span className="scrim"># full guide: README · tables: RESULTS.md</span></div>
          </div>
        </Reveal>

        <Reveal className="footer__cite" delay={0.06}>
          <span className="divider-num">CITE</span>
          <pre className="footer__bib mono">{`@article{li2026preact,
  title   = {PreAct: Computer-Using Agents that
             Get Faster on Repeated Tasks},
  author  = {Li, Bojie},
  journal = {arXiv preprint arXiv:2606.17929},
  year    = {2026},
}`}</pre>
        </Reveal>

        <div className="footer__bottom">
          <div className="footer__brand">
            <span className="footer__mark" aria-hidden />
            <span className="mono">PreAct · Pine AI · 2026</span>
          </div>
          <nav className="footer__nav mono">
            <a href="#programs">Programs</a>
            <a href="#demo">The check</a>
            <a href="#results">Results</a>
          </nav>
        </div>
      </div>
    </footer>
  )
}
