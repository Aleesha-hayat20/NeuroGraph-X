// Footer line that says what GET /health returned, or why it could not be reached.
// A failure is shown as text, never as a blank page (memo 0012).
// `status` comes from useHealth() in the layout.
export default function ApiStatus({ status }) {
  if (status.state === 'loading') return <span>API: checking...</span>
  if (status.state === 'error') return <span className="api-error">API: {status.message}</span>

  const { health } = status
  return (
    <span>
      API: {health.status}, version {health.version}
      {health.data_mode ? `, data: ${health.data_mode}` : ''}
    </span>
  )
}
