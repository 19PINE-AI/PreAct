import { motion, useReducedMotion } from 'framer-motion'
import { HEADLINES } from '../data/results'
import HeroGraph from './HeroGraph'
import './Hero.css'

export default function Hero() {
  const reduce = useReducedMotion()
  const stagger = {
    hidden: {},
    show: { transition: { staggerChildren: reduce ? 0 : 0.09, delayChildren: reduce ? 0 : 0.15 } },
  }
  const item = {
    hidden: { opacity: reduce ? 1 : 0, y: reduce ? 0 : 28 },
    show: { opacity: 1, y: 0, transition: { duration: reduce ? 0 : 0.8, ease: [0.22, 1, 0.36, 1] } },
  }
  return (
    <header className="hero" id="top">
      <HeroGraph />
      <div className="hero__inner shell">
        <motion.div variants={stagger} initial="hidden" animate="show" className="hero__copy">
          <motion.div variants={item} className="hero__badge">
            <span className="dot bg-pass" /> Pine AI · Computer-Using Agents
          </motion.div>

          <motion.h1 variants={item} className="hero__title">
            Agents that get faster on<br />the tasks they repeat.
          </motion.h1>

          <motion.p variants={item} className="hero__lede">
            A computer-using agent redoes a task from scratch every time, even one it finished
            yesterday. <strong>PreAct</strong> turns the first success into a small program it can
            replay, so the same task costs about an order of magnitude less the next time — and it
            checks every program against a clean run before it trusts it.
          </motion.p>

          <motion.div variants={item} className="hero__paper">
            <span className="mono">Paper: Computer-Using Agents that Get Faster on Repeated Tasks</span>
          </motion.div>

          <motion.div variants={item} className="hero__cta">
            <a href="#architecture" className="btn btn-primary">See how it works →</a>
            <a href="#corpus" className="btn">Browse real programs</a>
          </motion.div>

          <motion.div variants={item} className="hero__stats">
            {HEADLINES.map((h) => (
              <div key={h.label} className="hero__stat">
                <div className={`hero__stat-val signal-${h.tone === 'neutral' ? '' : h.tone}`}>
                  {h.value} <span className="hero__stat-unit">{h.unit}</span>
                </div>
                <div className="hero__stat-label">{h.label}</div>
              </div>
            ))}
          </motion.div>
        </motion.div>
      </div>
      <div className="hero__loop-legend mono">
        <span className="signal-replay">● find a saved program</span>
        <span className="signal-amber">● fall back to the full agent</span>
        <span className="signal-pass">● check, then save</span>
      </div>
    </header>
  )
}
