import './PhoneFrame.css'

// A small Android-style device bezel that frames a (downscaled) real screenshot.
export default function PhoneFrame({ src, badge, dim = false }) {
  const base = import.meta.env.BASE_URL || '/'
  return (
    <div className="phone">
      <div className="phone__bezel">
        <span className="phone__cam" />
        <div className="phone__screen">
          {src ? (
            <img className={`phone__shot ${dim ? 'is-dim' : ''}`} src={base + src} alt="" loading="lazy" />
          ) : (
            <div className="phone__blank" />
          )}
          {badge && (
            <div className={`phone__badge phone__badge--${badge.tone}`}>{badge.text}</div>
          )}
        </div>
      </div>
    </div>
  )
}
