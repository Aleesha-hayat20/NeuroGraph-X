import { useEffect, useState } from 'react'
import { getExclusions } from '../api/client.js'

// Exclusions page (W7-15): every participant removed by quality control, with the first gate
// failed, every gate failed and every reason (memo 0003). The gate filter runs in the browser,
// so the counts per gate always cover the whole log.
const GATES = ['rater', 'motion', 'completeness']

export default function Exclusions() {
  const [state, setState] = useState({ status: 'loading' })
  const [gate, setGate] = useState('')

  useEffect(() => {
    let cancelled = false
    getExclusions()
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
        <h1>Exclusions</h1>
        <p className="muted">Loading exclusions...</p>
      </section>
    )
  }

  if (state.status === 'error') {
    return (
      <section>
        <h1>Exclusions</h1>
        <p className="api-error">Could not load exclusions. {state.message}</p>
      </section>
    )
  }

  const { total, exclusions } = state.data
  const countOf = (g) => exclusions.filter((e) => e.first_gate_failed === g).length
  const shown = gate ? exclusions.filter((e) => e.first_gate_failed === gate) : exclusions

  return (
    <section>
      <h1>Exclusions</h1>
      <p>
        {total} participants excluded by quality control. First gate failed:{' '}
        {GATES.map((g) => `${g} ${countOf(g)}`).join(', ')}.
      </p>

      <div className="filters">
        <label>
          First gate failed
          <select value={gate} onChange={(event) => setGate(event.target.value)}>
            <option value="">All gates</option>
            {GATES.map((g) => (
              <option key={g} value={g}>
                {g}
              </option>
            ))}
          </select>
        </label>
        <button type="button" onClick={() => setGate('')}>
          Reset filters
        </button>
      </div>
      <p className="muted">
        Showing {shown.length} of {exclusions.length}.
      </p>

      {shown.length === 0 ? (
        <p className="muted">
          {total === 0 ? 'No participants were excluded.' : 'No exclusions match this gate.'}
        </p>
      ) : (
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Participant</th>
                <th>Site</th>
                <th>Group</th>
                <th>First gate failed</th>
                <th>All gates failed</th>
                <th>Reasons</th>
              </tr>
            </thead>
            <tbody>
              {shown.map((e) => (
                <tr key={e.participant_id}>
                  <td>{e.participant_id}</td>
                  <td>{e.site ?? '-'}</td>
                  <td>{e.group ?? '-'}</td>
                  <td>{e.first_gate_failed}</td>
                  <td>{e.gates_failed.join(', ')}</td>
                  <td>{e.reasons.length ? e.reasons.join('; ') : '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}