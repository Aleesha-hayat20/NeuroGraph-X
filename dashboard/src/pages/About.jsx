import { useHealth } from '../api/useHealth.js'

const TEAM = [
  ['Aleesha Hayat', 'Data and model engineer, team lead'],
  ['Laiba Afridi', 'Model and backend engineer'],
  ['Alishba Fayaz', 'Frontend and systems engineer'],
]

function ApiVersion({ status }) {
  if (status.state === 'loading') return <p className="muted">Checking the API...</p>
  if (status.state === 'error') return <p className="api-error">API: {status.message}</p>

  const { health } = status
  return (
    <p>
      API version {health.version}
      {health.data_mode ? `, data mode: ${health.data_mode}` : ''}.
    </p>
  )
}

export default function About() {
  const status = useHealth()

  return (
    <section>
      <h1>About</h1>
      <p>
        NeuroGraph-X analyses resting-state fMRI connectomes from the ABIDE dataset with a
        graph neural network, for autism research. It offers four atlases: AAL, CC200,
        Harvard-Oxford and Dosenbach 160.
      </p>

      <h2>Research use only</h2>
      <p>
        NeuroGraph-X is a research analysis tool. It does not diagnose, and it is not a
        medical device. A result informs the next step of a study. It is never a basis for a
        clinical decision about a person.
      </p>

      <h2>Version</h2>
      <ApiVersion status={status} />

      <h2>Team</h2>
      <p className="muted">Final Year Project, FAST-NUCES Peshawar. Supervisor: Dr. Hafeez Anwar.</p>
      <ul>
        {TEAM.map(([name, role]) => (
          <li key={name}>
            <strong>{name}</strong>: {role}
          </li>
        ))}
      </ul>
    </section>
  )
}