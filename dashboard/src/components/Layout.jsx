import { NavLink, Outlet } from 'react-router-dom'
import logo from '../assets/logo.png'
import ApiStatus from './ApiStatus.jsx'
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
      <main>
        <Outlet />
      </main>
      <footer className="layout-footer">
        <ApiStatus />
      </footer>
    </div>
  )
}
