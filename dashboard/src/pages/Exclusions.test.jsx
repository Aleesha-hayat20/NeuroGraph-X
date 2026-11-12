import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { getExclusions } from '../api/client.js'
import Exclusions from './Exclusions.jsx'

// The page is tested without a server: the API client is replaced by a stand-in.
vi.mock('../api/client.js', () => ({ getExclusions: vi.fn() }))

// Invented exclusions in the shape of GET /exclusions (memo 0013).
const RESPONSE = {
  total: 3,
  exclusions: [
    {
      participant_id: '0090007', file_id: null, site: 'SYN_B', group: 'autism',
      first_gate_failed: 'rater', gates_failed: ['rater'], reasons: ['qc_rater_1 = fail'],
    },
    {
      participant_id: '0090008', file_id: 'b2', site: 'SYN_A', group: 'control',
      first_gate_failed: 'motion', gates_failed: ['motion'],
      reasons: ['func_mean_fd = 0.602 > 0.5'],
    },
    {
      participant_id: '0090009', file_id: 'b3', site: 'SYN_A', group: null,
      first_gate_failed: 'rater', gates_failed: ['rater', 'motion'],
      reasons: ['qc_rater_1 = fail', 'func_mean_fd missing'],
    },
  ],
}

describe('Exclusions page', () => {
  beforeEach(() => {
    vi.resetAllMocks()
  })

  it('shows the total, the count per first gate and one row per exclusion', async () => {
    getExclusions.mockResolvedValue(RESPONSE)
    render(<Exclusions />)

    expect(
      await screen.findByText(
        '3 participants excluded by quality control. First gate failed: rater 2, motion 1, completeness 0.',
      ),
    ).toBeInTheDocument()
    expect(screen.getAllByRole('row')).toHaveLength(4) // the header and three exclusions
    expect(screen.getByText('Showing 3 of 3.')).toBeInTheDocument()
  })

  it('shows every gate failed and every reason, and a dash for a missing group', async () => {
    getExclusions.mockResolvedValue(RESPONSE)
    render(<Exclusions />)

    const row = (await screen.findByText('0090009')).closest('tr')
    expect(within(row).getByText('rater, motion')).toBeInTheDocument()
    expect(
      within(row).getByText('qc_rater_1 = fail; func_mean_fd missing'),
    ).toBeInTheDocument()
    expect(within(row).getByText('-')).toBeInTheDocument()
  })

  it('filters by first gate failed and resets', async () => {
    const user = userEvent.setup()
    getExclusions.mockResolvedValue(RESPONSE)
    render(<Exclusions />)
    await screen.findByText('0090007')

    await user.selectOptions(screen.getByLabelText('First gate failed'), 'motion')
    expect(screen.getByText('Showing 1 of 3.')).toBeInTheDocument()
    expect(screen.getByText('0090008')).toBeInTheDocument()
    expect(screen.queryByText('0090007')).not.toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Reset filters' }))
    expect(screen.getByText('Showing 3 of 3.')).toBeInTheDocument()
  })

  it('says so when no exclusion matches the gate', async () => {
    const user = userEvent.setup()
    getExclusions.mockResolvedValue(RESPONSE)
    render(<Exclusions />)
    await screen.findByText('0090007')

    await user.selectOptions(screen.getByLabelText('First gate failed'), 'completeness')

    expect(screen.getByText('No exclusions match this gate.')).toBeInTheDocument()
    expect(screen.queryByRole('table')).not.toBeInTheDocument()
  })

  it('says so when nobody was excluded', async () => {
    getExclusions.mockResolvedValue({ total: 0, exclusions: [] })
    render(<Exclusions />)

    expect(await screen.findByText('No participants were excluded.')).toBeInTheDocument()
    expect(screen.queryByRole('table')).not.toBeInTheDocument()
  })

  it('shows the API error in plain words instead of a table', async () => {
    getExclusions.mockRejectedValue(
      new Error('The API is not reachable. Check that the server is running.'),
    )
    render(<Exclusions />)

    const message = await screen.findByText(/Could not load exclusions/)
    expect(message).toHaveTextContent('The API is not reachable. Check that the server is running.')
    expect(screen.queryByRole('table')).not.toBeInTheDocument()
  })
})