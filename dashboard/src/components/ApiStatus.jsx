import { useEffect, useState } from 'react'
import { getHealth } from '../api/client.js'

// Smoke test of the API client and the dev proxy: asks GET /health once and says what happened.
// A failure is shown as text, never as a blank page (memo 0012).
// Later this is also where a "fixture data" marker appears, once /health reports the data mode.
export default function ApiStatus() {
  const [status, setStatus] = useState({ state: 'loading' })

  useEffect(() => {
    let cancelled = false
    getHealth()
      .then((health) => {
        if (!cancelled) setStatus({ state: 'ok', health })
      })
      .catch((error) => {
        if (!cancelled) setStatus({ state: 'error', message: error.message })
      })
    return () => {
      cancelled = true
    }
  }, [])

  if (status.state === 'loading') return <span>API: checking...</span>
  if (status.state === 'error') return <span className="api-error">API: {status.message}</span>
  return (
    <span>
      API: {status.health.status}, version {status.health.version}
    </span>
  )
}
