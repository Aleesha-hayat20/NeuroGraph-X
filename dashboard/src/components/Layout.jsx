import { NavLink, Outlet } from 'react-router-dom'
import { useHealth } from '../api/useHealth.js'
import logo from '../assets/logo.png'
import ApiStatus from './ApiStatus.jsx'
import FixtureNotice from './FixtureNotice.jsx'
import ResearchNotice from './ResearchNotice.jsx'

// The seven pages of memo 0012, in the order of the dashboard's use cases.
const PAGES = [
  { to: '/', label: 'Overview', end: true },
  { to: '/participants', label: 'Participants' },
  { to: '/analysis', label: 'Analysis' },
  { to: '/history', label: 'History' },
  { to: '/models', label: 'Models' },
  { to: '/exclusions', label: 'Exclusions' },
  { to: '/about', label: 'About' },
]

export default function Layout() {
  const health = useHealth()
  const onFixtures = health.state === 'ok' && health.health.data_mode === 'fixtures'

  return (
    <div className="layout">
      <header className="layout-header">
        <span className="brand">
          <img src={logo} alt="" width="32" height="32" />
          NeuroGraph-X
        </span>
        <nav aria-label="Pages">
          {PAGES.map((page) => (
            <NavLink key={page.to} to={page.to} end={page.end}>
              {page.label}
            </NavLink>
          ))}
        </nav>
      </header>
      <ResearchNotice />
      {onFixtures && <FixtureNotice />}
      <main>
        <Outlet />
      </main>
      <footer className="layout-footer">
        <ApiStatus status={health} />
      </footer>
    </div>
  )
}
