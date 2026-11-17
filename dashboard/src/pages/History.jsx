import { Fragment, useEffect, useState } from 'react'
import { exportUrl, getAnalyses, getAnalysis, regenerateAnalysis } from '../api/client.js'

// History page (W6-12): past analyses, newest first (GET /analyses), filtered by participant
// and atlas by the API. "Open" shows all ten fields of one record (GET /analyses/{id}),
// memo 0013. Confidence is shown as "Confidence in this prediction" and marked
// "not calibrated" while the record's calibrated flag is false (memo 0012).
// W7-17: an open record can be exported as JSON or CSV and regenerated with its original
// model; the page says whether the repeat is identical to the original.
const NO_FILTERS = { participant: '', atlas: '' }

// The atlas keys the API accepts, with the names used elsewhere in the project.
const ATLASES = [
  { key: 'aal', label: 'AAL' },
  { key: 'cc200', label: 'CC200' },
  { key: 'ho', label: 'Harvard-Oxford' },
  { key: 'dosenbach160', label: 'Dosenbach 160' },
]

function atlasLabel(key) {
  const found = ATLASES.find((atlas) => atlas.key === key)
  return found ? found.label : key
}

function formatTime(timestamp) {
  return timestamp.slice(0, 19).replace('T', ' ')
}

function percent(confidence) {
  return `${(confidence * 100).toFixed(1)}%`
}

function confidenceText(record) {
  return `${percent(record.confidence)} (${record.calibrated ? 'calibrated' : 'not calibrated'})`
}

// The ten fields of an analysis record (memo 0013), in the order of the schema.
function detailRows(record) {
  return [
    ['Analysis ID', record.analysis_id],
    ['Time (UTC)', formatTime(record.timestamp)],
    ['Participant', record.participant_id],
    ['Atlas', atlasLabel(record.atlas)],
    ['Run ID', record.run_id],
    ['Prediction', record.prediction],
    ['Confidence in this prediction', confidenceText(record)],
    ['Calibrated', record.calibrated ? 'yes' : 'no'],
    ['Git commit', record.git_commit ?? 'not recorded'],
    ['Reproduces analysis', record.reproduces_analysis_id ?? 'none (original analysis)'],
  ]
}

// What a regenerate returned: is the repeat identical, and what did each run say.
function RegenerateOutcome({ result, onOpen }) {
  const { analysis, original, identical, differences } = result
  return (
    <div className="regenerate-result">
      <p>
        <strong>
          {identical
            ? 'Identical to the original.'
            : `Not identical to the original. Different: ${differences.join(', ')}.`}
        </strong>
      </p>
      <p>
        {`Original ${original.analysis_id}: ${original.prediction}, ${confidenceText(original)}.`}
      </p>
      <p>
        {`Regenerated ${analysis.analysis_id}: ${analysis.prediction}, ${confidenceText(analysis)}.`}
      </p>
      <p className="muted">
        The regenerated analysis was added to the history. Its record names the original in
        &quot;Reproduces analysis&quot;.
      </p>
      <button type="button" onClick={() => onOpen(analysis.analysis_id)}>
        Open the new analysis
      </button>
    </div>
  )
}

export default function History() {
  const [form, setForm] = useState(NO_FILTERS) // what is typed or chosen
  const [applied, setApplied] = useState(NO_FILTERS) // what the list was loaded with
  const [reloads, setReloads] = useState(0) // raised after a regenerate to reload the list
  const [result, setResult] = useState({ key: null, data: null, error: null })
  const [detail, setDetail] = useState(null) // { id, record, error } for the open record
  const [regen, setRegen] = useState(null) // { id, status, result?, message? } for a regenerate

  const key = `${applied.participant}|${applied.atlas}|${reloads}`
  const loading = result.key !== key
  const filtered = applied.participant !== '' || applied.atlas !== ''

  useEffect(() => {
    let cancelled = false
    getAnalyses({ participant_id: applied.participant.trim(), atlas: applied.atlas })
      .then((data) => {
        if (!cancelled) setResult({ key, data, error: null })
      })
      .catch((error) => {
        if (!cancelled) setResult({ key, data: null, error: error.message })
      })
    return () => {
      cancelled = true
    }
  }, [applied, key])

  function change(name) {
    return (event) => setForm({ ...form, [name]: event.target.value })
  }

  function handleApply(event) {
    event.preventDefault()
    setApplied(form)
    setDetail(null)
    setRegen(null)
  }

  function handleReset() {
    setForm(NO_FILTERS)
    setApplied(NO_FILTERS)
    setDetail(null)
    setRegen(null)
  }

  function closeRecord() {
    setDetail(null)
    setRegen(null)
  }

  function openRecord(id) {
    setDetail({ id, record: null, error: null })
    getAnalysis(id)
      .then((record) => {
        setDetail((current) => (current && current.id === id ? { id, record, error: null } : current))
      })
      .catch((error) => {
        setDetail((current) =>
          current && current.id === id ? { id, record: null, error: error.message } : current,
        )
      })
  }

  function regenerate(id) {
    setRegen({ id, status: 'running' })
    regenerateAnalysis(id)
      .then((outcome) => {
        setRegen((current) =>
          current && current.id === id ? { id, status: 'ok', result: outcome } : current,
        )
        setReloads((count) => count + 1)
      })
      .catch((error) => {
        setRegen((current) =>
          current && current.id === id ? { id, status: 'error', message: error.message } : current,
        )
      })
  }

  let content
  if (loading) {
    content = <p className="muted">Loading analyses...</p>
  } else if (result.error) {
    content = <p className="api-error">Could not load analyses. {result.error}</p>
  } else if (result.data.total === 0) {
    content = (
      <p className="muted">
        {filtered ? 'No analyses match these filters.' : 'No analyses have been run yet.'}
      </p>
    )
  } else {
    const { total, analyses } = result.data
    content = (
      <>
        <p className="muted">
          Showing {analyses.length} of {total} analyses, newest first.
        </p>
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Time (UTC)</th>
                <th>Participant</th>
                <th>Atlas</th>
                <th>Prediction</th>
                <th>Confidence in this prediction</th>
                <th>Record</th>
              </tr>
            </thead>
            <tbody>
              {analyses.map((a) => (
                <tr key={a.analysis_id}>
                  <td>{formatTime(a.timestamp)}</td>
                  <td>{a.participant_id}</td>
                  <td>{atlasLabel(a.atlas)}</td>
                  <td>{a.prediction}</td>
                  <td>
                    {percent(a.confidence)}
                    {!a.calibrated && <span className="muted"> (not calibrated)</span>}
                  </td>
                  <td>
                    <button
                      type="button"
                      aria-label={`Open analysis ${a.analysis_id}`}
                      onClick={() => openRecord(a.analysis_id)}
                    >
                      Open
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </>
    )
  }

  return (
    <section>
      <h1>History</h1>

      <form className="filters" onSubmit={handleApply}>
        <label>
          Participant
          <input
            type="text"
            value={form.participant}
            placeholder="0050003 or 50003"
            onChange={change('participant')}
          />
        </label>
        <label>
          Atlas
          <select value={form.atlas} onChange={change('atlas')}>
            <option value="">All atlases</option>
            {ATLASES.map((atlas) => (
              <option key={atlas.key} value={atlas.key}>
                {atlas.label}
              </option>
            ))}
          </select>
        </label>
        <button type="submit">Apply filters</button>
        <button type="button" onClick={handleReset}>
          Reset filters
        </button>
      </form>

      {content}

      {detail && (
        <section className="detail-panel" aria-label="Analysis record">
          <div className="detail-header">
            <h2>Analysis {detail.id}</h2>
            <button type="button" onClick={closeRecord}>
              Close
            </button>
          </div>
          {detail.error && <p className="api-error">Could not load this record. {detail.error}</p>}
          {!detail.record && !detail.error && <p className="muted">Loading record...</p>}
          {detail.record && (
            <>
              <dl className="detail-list">
                {detailRows(detail.record).map(([label, value]) => (
                  <Fragment key={label}>
                    <dt>{label}</dt>
                    <dd>{value}</dd>
                  </Fragment>
                ))}
              </dl>

              <div className="filters">
                <a href={exportUrl(detail.id, 'json')} download>
                  Export JSON
                </a>
                <a href={exportUrl(detail.id, 'csv')} download>
                  Export CSV
                </a>
                <button
                  type="button"
                  onClick={() => regenerate(detail.id)}
                  disabled={regen !== null && regen.id === detail.id && regen.status === 'running'}
                >
                  Regenerate
                </button>
                {detail.record.reproduces_analysis_id && (
                  <button type="button" onClick={() => openRecord(detail.record.reproduces_analysis_id)}>
                    Open original analysis
                  </button>
                )}
              </div>

              {regen && regen.id === detail.id && (
                <div aria-live="polite">
                  {regen.status === 'running' && <p className="muted">Regenerating...</p>}
                  {regen.status === 'error' && (
                    <p className="api-error">Could not regenerate this analysis. {regen.message}</p>
                  )}
                  {regen.status === 'ok' && <RegenerateOutcome result={regen.result} onOpen={openRecord} />}
                </div>
              )}
            </>
          )}
        </section>
      )}
    </section>
  )
}