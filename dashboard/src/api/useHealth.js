import { useEffect, useState } from 'react'
import { getHealth } from './client.js'

// One call to GET /health, made once when the layout mounts and shared by the footer
// status and the fixture-data banner (memo 0012). A failure becomes text, never a blank page.
export function useHealth() {
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

  return status
}
