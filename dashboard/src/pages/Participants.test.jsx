import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { getParticipants } from '../api/client.js'
import Participants from './Participants.jsx'

// The page is tested without a server: the API client is replaced by a stand-in.
vi.mock('../api/client.js', () => ({ getParticipants: vi.fn() }))

// Invented participants in the shape of GET /participants (memo 0013).
const RESPONSE = {
  total: 3,
  included: 2,
  excluded: 1,
  participants: [
    {
      participant_id: '0090001', file_id: 'a1', site: 'SYN_A', group: 'autism', sex: 'male',
      age: 28.23, qc_status: 'included', exclusion_gate: null, exclusion_reasons: [], split: 'frozen',
    },
    {
      participant_id: '0090002', file_id: 'a2', site: 'SYN_A', group: 'control', sex: 'male',
      age: 26.1, qc_status: 'included', exclusion_gate: null, exclusion_reasons: [], split: 'development',
    },
    {
      participant_id: '0090007', file_id: null, site: 'SYN_B', group: 'autism', sex: 'male',
      age: 26.25, qc_status: 'excluded', exclusion_gate: 'rater',
      exclusion_reasons: ['qc_rater_1 = fail'], split: null,
    },
  ],
}

// Stands in for the Analysis page, so the test can see where Run sent the user.
function Where() {
  const location = useLocation()
  return (
    <p>
      Now at {location.pathname}
      {location.search}
    </p>
  )
}

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/participants']}>
      <Routes>
        <Route path="/participants" element={<Participants />} />
        <Route path="/analysis" element={<Where />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('Participants page', () => {
  beforeEach(() => {
    vi.resetAllMocks()
  })

  it('shows the counts and one row per participant', async () => {
    getParticipants.mockResolvedValue(RESPONSE)
    renderPage()

    expect(await screen.findByText('3 participants: 2 included, 1 excluded.')).toBeInTheDocument()
    expect(screen.getAllByRole('row')).toHaveLength(4) // the header and three participants
    expect(screen.getByText('Showing 3 of 3.')).toBeInTheDocument()
  })

  it('shows the reason and disables Run for an excluded participant', async () => {
    getParticipants.mockResolvedValue(RESPONSE)
    renderPage()

    const excludedRow = (await screen.findByText('0090007')).closest('tr')
    expect(within(excludedRow).getByText('qc_rater_1 = fail')).toBeInTheDocument()
    expect(within(excludedRow).getByRole('button', { name: 'Run' })).toBeDisabled()

    const includedRow = screen.getByText('0090001').closest('tr')
    expect(within(includedRow).getByRole('button', { name: 'Run' })).toBeEnabled()
  })

  it('combines the site, group and quality filters', async () => {
    const user = userEvent.setup()
    getParticipants.mockResolvedValue(RESPONSE)
    renderPage()
    await screen.findByText('0090001')

    await user.selectOptions(screen.getByLabelText('Quality'), 'excluded')
    expect(screen.getByText('Showing 1 of 3.')).toBeInTheDocument()
    expect(screen.getByText('0090007')).toBeInTheDocument()
    expect(screen.queryByText('0090001')).not.toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Reset filters' }))
    expect(screen.getByText('Showing 3 of 3.')).toBeInTheDocument()

    await user.selectOptions(screen.getByLabelText('Site'), 'SYN_A')
    await user.selectOptions(screen.getByLabelText('Group'), 'control')
    expect(screen.getByText('Showing 1 of 3.')).toBeInTheDocument()
    expect(screen.getByText('0090002')).toBeInTheDocument()
  })

  it('says so when no participant matches the filters', async () => {
    const user = userEvent.setup()
    getParticipants.mockResolvedValue(RESPONSE)
    renderPage()
    await screen.findByText('0090001')

    await user.selectOptions(screen.getByLabelText('Site'), 'SYN_B')
    await user.selectOptions(screen.getByLabelText('Quality'), 'included')

    expect(screen.getByText('No participants match these filters.')).toBeInTheDocument()
    expect(screen.queryByRole('table')).not.toBeInTheDocument()
  })

  it('opens the Analysis page for the chosen participant', async () => {
    const user = userEvent.setup()
    getParticipants.mockResolvedValue(RESPONSE)
    renderPage()

    const row = (await screen.findByText('0090001')).closest('tr')
    await user.click(within(row).getByRole('button', { name: 'Run' }))

    expect(screen.getByText('Now at /analysis?participant=0090001')).toBeInTheDocument()
  })

  it('shows the API error in plain words instead of a table', async () => {
    getParticipants.mockRejectedValue(
      new Error('The API is not reachable. Check that the server is running.'),
    )
    renderPage()

    const message = await screen.findByText(/Could not load participants/)
    expect(message).toHaveTextContent('The API is not reachable. Check that the server is running.')
    expect(screen.queryByRole('table')).not.toBeInTheDocument()
  })
})