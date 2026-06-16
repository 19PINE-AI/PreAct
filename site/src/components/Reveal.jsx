import { motion, useReducedMotion } from 'framer-motion'

// Scroll-triggered staggered reveal used throughout the site.
// When the visitor prefers reduced motion we render plain, fully-visible
// markup with no animation at all.
export default function Reveal({ children, delay = 0, y = 26, className, as = 'div' }) {
  const reduce = useReducedMotion()

  if (reduce) {
    const Tag = as
    return <Tag className={className}>{children}</Tag>
  }

  const M = motion[as] || motion.div
  return (
    <M
      className={className}
      initial={{ opacity: 0, y }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: '-60px' }}
      transition={{ duration: 0.7, delay, ease: [0.22, 1, 0.36, 1] }}
    >
      {children}
    </M>
  )
}
