import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { createAnalysis, getAtlases, getParticipants } from '../api/client.js'
import ResultCard from '../components/ResultCard.jsx'

// Analysis page (W5-15). Choose a participant and an atlas, run, show the result or the error.
// The participant can come from the Participants page as /analysis?participant=<id>.
export default function Analysis() {
  const [searchParams] = useSearchParams()
  const [setup, setSetup] = useState({ status: 'loading' })
  const [participantId, setParticipantId] = useState(searchParams.get('participant') ?? '')
  const [atlas, setAtlas] = useState('')
  const [run, setRun] = useState({ status: 'idle' })

  useEffect(() => {
    let cancelled = false
    Promise.all([getAtlases(), getParticipants({ qc_status: 'included' })])
      .then(([atlases, list]) => {
        if (!cancelled) setSetup({ status: 'ok', atlases, participants: list.participants })
      })
      .catch((error) => {
        if (!cancelled) setSetup({ status: 'error', message: error.message })
      })
    return () => {
      cancelled = true
    }
  }, [])

  if (setup.status === 'loading') {
    return (
      <section>
        <h1>Analysis</h1>
        <p className="muted">Loading...</p>
      </section>
    )
  }

  if (setup.status === 'error') {
    return (
      <section>
        <h1>Analysis</h1>
        <p className="api-error">Could not load the analysis options. {setup.message}</p>
      </section>
    )
  }

  const { atlases, participants } = setup
  // A participant named in the address that is not in the included list stays selectable,
  // so the API's own answer (for example 409, excluded) is what the user sees.
  const listed = participants.some((p) => p.participant_id === participantId)
  const running = run.status === 'running'

  function handleRun(event) {
    event.preventDefault()
    setRun({ status: 'running' })
    createAnalysis(participantId, atlas)
      .then((record) => setRun({ status: 'ok', record }))
      .catch((error) => setRun({ status: 'error', message: error.message }))
  }

  return (
    <section>
      <h1>Analysis</h1>
      <p className="muted">Choose an included participant and an atlas, then run the analysis.</p>

      <form className="analysis-form" onSubmit={handleRun}>
        <label>
          Participant
          <select value={participantId} onChange={(event) => setParticipantId(event.target.value)}>
            <option value="">Choose a participant</option>
            {participantId && !listed && (
              <option value={participantId}>{participantId} (not in the included list)</option>
            )}
            {participants.map((p) => (
              <option key={p.participant_id} value={p.participant_id}>
                {p.participant_id} ({p.site}, {p.group})
              </option>
            ))}
          </select>
        </label>

        <fieldset className="atlas-options">
          <legend>Atlas</legend>
          {atlases.map((a) => (
            <label key={a.atlas}>
              <input
                type="radio"
                name="atlas"
                value={a.atlas}
                checked={atlas === a.atlas}
                onChange={() => setAtlas(a.atlas)}
              />
              {a.label} ({a.n_regions} regions)
              {!a.data_available && <small className="muted"> no connectomes</small>}
              {a.data_available && !a.model_registered && (
                <small className="muted"> no model registered</small>
              )}
            </label>
          ))}
        </fieldset>

        <button type="submit" disabled={!participantId || !atlas || running}>
          {running ? 'Running...' : 'Run analysis'}
        </button>
      </form>

      {run.status === 'error' && (
        <p className="api-error" role="alert">
          {run.message}
        </p>
      )}
     {run.status === 'ok' && <ResultCard record={run.record} />}
    </section>
  )
}