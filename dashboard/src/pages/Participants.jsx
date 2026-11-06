import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getParticipants } from '../api/client.js'

// Participants page (W5-14): table, site / group / quality filters, quality badge and Run.
// The filters run in the browser: GET /participants only filters by qc_status today.
const NO_FILTERS = { site: '', group: '', quality: '' }

export default function Participants() {
  const [state, setState] = useState({ status: 'loading' })
  const [filters, setFilters] = useState(NO_FILTERS)
  const navigate = useNavigate()

  useEffect(() => {
    let cancelled = false
    getParticipants()
      .then((data) => {
        if (!cancelled) setState({ status: 'ok', data })
      })
      .catch((error) => {
        if (!cancelled) setState({ status: 'error', message: error.message })
      })
    return () => {
      cancelled = true
    }
  }, [])

  if (state.status === 'loading') {
    return (
      <section>
        <h1>Participants</h1>
        <p className="muted">Loading participants...</p>
      </section>
    )
  }

  if (state.status === 'error') {
    return (
      <section>
        <h1>Participants</h1>
        <p className="api-error">Could not load participants. {state.message}</p>
      </section>
    )
  }

  const { total, included, excluded, participants } = state.data
  const sites = [...new Set(participants.map((p) => p.site).filter(Boolean))].sort()
  const shown = participants.filter(
    (p) =>
      (!filters.site || p.site === filters.site) &&
      (!filters.group || p.group === filters.group) &&
      (!filters.quality || p.qc_status === filters.quality),
  )

  function change(name) {
    return (event) => setFilters({ ...filters, [name]: event.target.value })
  }

  return (
    <section>
      <h1>Participants</h1>
      <p>
        {total} participants: {included} included, {excluded} excluded.
      </p>

      <div className="filters">
        <label>
          Site
          <select value={filters.site} onChange={change('site')}>
            <option value="">All sites</option>
            {sites.map((site) => (
              <option key={site} value={site}>
                {site}
              </option>
            ))}
          </select>
        </label>
        <label>
          Group
          <select value={filters.group} onChange={change('group')}>
            <option value="">All groups</option>
            <option value="autism">autism</option>
            <option value="control">control</option>
          </select>
        </label>
        <label>
          Quality
          <select value={filters.quality} onChange={change('quality')}>
            <option value="">All</option>
            <option value="included">included</option>
            <option value="excluded">excluded</option>
          </select>
        </label>
        <button type="button" onClick={() => setFilters(NO_FILTERS)}>
          Reset filters
        </button>
      </div>
      <p className="muted">
        Showing {shown.length} of {participants.length}.
      </p>

      {shown.length === 0 ? (
        <p className="muted">No participants match these filters.</p>
      ) : (
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Participant</th>
                <th>Site</th>
                <th>Group</th>
                <th>Sex</th>
                <th>Age</th>
                <th>Quality</th>
                <th>Exclusion reason</th>
                <th>Run</th>
              </tr>
            </thead>
            <tbody>
              {shown.map((p) => {
                const isExcluded = p.qc_status === 'excluded'
                return (
                  <tr key={p.participant_id}>
                    <td>{p.participant_id}</td>
                    <td>{p.site ?? '-'}</td>
                    <td>{p.group ?? '-'}</td>
                    <td>{p.sex ?? '-'}</td>
                    <td>{p.age ?? '-'}</td>
                    <td>
                      <span className={`badge badge-${p.qc_status}`}>{p.qc_status}</span>
                    </td>
                    <td>{p.exclusion_reasons.length ? p.exclusion_reasons.join('; ') : '-'}</td>
                    <td>
                      <button
                        type="button"
                        disabled={isExcluded}
                        title={isExcluded ? 'An excluded participant cannot be analysed.' : undefined}
                        onClick={() => navigate(`/analysis?participant=${p.participant_id}`)}
                      >
                        Run
                      </button>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}