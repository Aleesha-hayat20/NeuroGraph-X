import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getCohortSummary } from '../api/client.js'

const GATES = [
  ['rater', 'Rater'],
  ['motion', 'Motion'],
  ['completeness', 'Completeness'],
]
const GROUPS = [
  ['autism', 'Autism'],
  ['control', 'Control'],
]
const SPLITS = [
  ['frozen', 'Frozen evaluation set'],
  ['development', 'Development'],
]

const fmt = (n) => n.toLocaleString('en-US')

// One horizontal bar: included part solid, excluded part faded. The bar length is
// the row total relative to the longest row, so rows can be compared.
function BarRow({ label, included, excluded, max }) {
  const total = included + excluded
  const width = max > 0 ? (total / max) * 100 : 0
  return (
    <li
      style={{
        display: 'grid',
        gridTemplateColumns: '8rem 1fr 15rem',
        gap: '0.75rem',
        alignItems: 'center',
        marginBottom: '0.4rem',
      }}
    >
      <span>{label}</span>
      <div>
        <span
          role="img"
          aria-label={`${label}: ${included} included, ${excluded} excluded`}
          style={{ display: 'flex', height: '1rem', width: `${width}%` }}
        >
          <span style={{ flex: included, background: 'currentColor' }} />
          <span style={{ flex: excluded, background: 'currentColor', opacity: 0.3 }} />
        </span>
      </div>
      <span className="muted">
        {fmt(included)} included · {fmt(excluded)} excluded
      </span>
    </li>
  )
}

function BarChart({ title, rows }) {
  const max = Math.max(0, ...rows.map((r) => r.included + r.excluded))
  return (
    <section>
      <h3>{title}</h3>
      <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
        {rows.map((r) => (
          <BarRow key={r.label} {...r} max={max} />
        ))}
      </ul>
    </section>
  )
}

export default function Overview() {
  const [state, setState] = useState({ status: 'loading' })

  useEffect(() => {
    let cancelled = false
    getCohortSummary()
      .then((data) => {
        if (!cancelled) setState({ status: 'ok', data })
      })
      .catch((err) => {
        if (!cancelled) setState({ status: 'error', message: err.message })
      })
    return () => {
      cancelled = true
    }
  }, [])

  if (state.status === 'loading') {
    return (
      <section>
        <h1>Overview</h1>
        <p className="muted">Loading cohort summary…</p>
      </section>
    )
  }

  if (state.status === 'error') {
    return (
      <section>
        <h1>Overview</h1>
        <p className="api-error">Could not load the cohort summary. {state.message}</p>
      </section>
    )
  }

  const d = state.data

  if (d.total === 0) {
    return (
      <section>
        <h1>Overview</h1>
        <p className="muted">No participants found.</p>
      </section>
    )
  }

  const groupRows = GROUPS.map(([key, label]) => ({ label, ...d.by_group[key] }))
  const siteRows = d.by_site.map((s) => ({ label: s.site, included: s.included, excluded: s.excluded }))

  return (
    <section>
      <h1>Overview</h1>
      <p>{`${fmt(d.total)} participants: ${fmt(d.included)} included, ${fmt(d.excluded)} excluded by quality control.`}</p>

      <div className="table-wrap">
        <table className="data-table">
          <caption>Excluded, by first gate failed</caption>
          <thead>
            <tr>
              <th>Gate</th>
              <th>Participants</th>
            </tr>
          </thead>
          <tbody>
            {GATES.map(([key, label]) => (
              <tr key={key}>
                <td>{label}</td>
                <td>{fmt(d.excluded_by_gate[key])}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p>
        <Link to="/exclusions">See every excluded participant and reason</Link>
      </p>

      <div className="table-wrap">
        <table className="data-table">
          <caption>Included, by split</caption>
          <thead>
            <tr>
              <th>Split</th>
              <th>Participants</th>
            </tr>
          </thead>
          <tbody>
            {SPLITS.map(([key, label]) => (
              <tr key={key}>
                <td>{label}</td>
                <td>{fmt(d.by_split[key])}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <p className="muted">Solid part of a bar = included, faded part = excluded.</p>
      <BarChart title="By group" rows={groupRows} />
      <BarChart title="By site" rows={siteRows} />
    </section>
  )
}