import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import Analysis from './Analysis.jsx'
import { createAnalysis, getAtlases, getParticipants } from '../api/client.js'

vi.mock('../api/client.js', () => ({
  createAnalysis: vi.fn(),
  getAtlases: vi.fn(),
  getParticipants: vi.fn(),
}))
vi.mock('../components/ResultCard.jsx', () => ({
  default: () => <p>result card</p>,
}))

const ATLASES = [
  { atlas: 'cc200', label: 'CC200', n_regions: 200, data_available: true, model_registered: true },
]
const PARTICIPANTS = [
  { participant_id: '0050011', site: 'PITT', group: 'autism', split: 'frozen' },
  { participant_id: '0050003', site: 'PITT', group: 'autism', split: 'development' },
]

beforeEach(() => {
  vi.clearAllMocks()
  getAtlases.mockResolvedValue(ATLASES)
  getParticipants.mockResolvedValue({ participants: PARTICIPANTS })
  createAnalysis.mockResolvedValue({ analysis_id: 'a1b2c3d4e5f6' })
})

async function openAnalysis() {
  render(
    <MemoryRouter>
      <Analysis />
    </MemoryRouter>,
  )
  await screen.findByRole('combobox')
}

async function run(participantId) {
  await openAnalysis()
  fireEvent.change(screen.getByRole('combobox'), { target: { value: participantId } })
  fireEvent.click(screen.getByRole('radio', { name: /CC200/ }))
  fireEvent.click(screen.getByRole('button', { name: 'Run analysis' }))
  await screen.findByText('result card')
}

describe('Analysis page: development-pool note (#198)', () => {
  it('says the prediction is not an independent test for a development participant', async () => {
    await run('0050003')
    expect(screen.getByText(/trained on all 761 development participants/)).toBeInTheDocument()
    expect(screen.getByText(/not an independent test/)).toBeInTheDocument()
  })

  it('shows no note for a participant in the frozen evaluation set', async () => {
    await run('0050011')
    expect(screen.queryByText(/not an independent test/)).not.toBeInTheDocument()
  })
})