import { useEffect, useState } from 'react'
import './Nav.css'

const LINKS = [
  ['problem', 'Problem'],
  ['architecture', 'How it works'],
  ['demo', 'Try it'],
  ['corpus', 'Programs'],
  ['trajectories', 'Real runs'],
  ['results', 'Results'],
]

export default function Nav() {
  const [active, setActive] = useState('problem')
  const [scrolled, setScrolled] = useState(false)

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 30)
    window.addEventListener('scroll', onScroll)
    const obs = new IntersectionObserver(
      (entries) => {
        entries.forEach((e) => {
          if (e.isIntersecting) setActive(e.target.id)
        })
      },
      { rootMargin: '-45% 0px -50% 0px' },
    )
    LINKS.forEach(([id]) => {
      const el = document.getElementById(id)
      if (el) obs.observe(el)
    })
    return () => {
      window.removeEventListener('scroll', onScroll)
      obs.disconnect()
    }
  }, [])

  return (
    <header className={`nav ${scrolled ? 'nav--scrolled' : ''}`}>
      <div className="nav__inner shell">
        <a href="#top" className="nav__brand">
          <span className="nav__mark" aria-hidden>
            <span className="nav__node" />
            <span className="nav__edge" />
            <span className="nav__node nav__node--pass" />
          </span>
          <span className="nav__name">PreAct</span>
        </a>
        <nav className="nav__links">
          {LINKS.map(([id, label]) => (
            <a key={id} href={`#${id}`} className={active === id ? 'is-active' : ''}>
              {label}
            </a>
          ))}
        </nav>
        <a className="nav__cta" href="#cite">Paper ↗</a>
      </div>
    </header>
  )
}
