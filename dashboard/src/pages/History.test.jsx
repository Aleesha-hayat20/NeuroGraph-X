import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { getAnalyses, getAnalysis } from '../api/client.js'
import History from './History.jsx'

// The page is tested without a server: the API client is replaced by a stand-in.
vi.mock('../api/client.js', () => ({ getAnalyses: vi.fn(), getAnalysis: vi.fn() }))

// Invented analyses in the shape of GET /analyses (memo 0013), newest first.
const NEWEST = {
  analysis_id: 'a1b2c3d4e5f6',
  timestamp: '2026-11-07T09:05:00+00:00',
  participant_id: '0090001',
  atlas: 'cc200',
  run_id: '1bf121a5',
  prediction: 'control',
  confidence: 0.7,
  calibrated: false,
  git_commit: null,
  reproduces_analysis_id: null,
}
const MIDDLE = {
  analysis_id: 'b2c3d4e5f6a1',
  timestamp: '2026-11-07T09:04:00+00:00',
  participant_id: '0090003',
  atlas: 'ho',
  run_id: '76533df4',
  prediction: 'autism',
  confidence: 0.58,
  calibrated: false,
  git_commit: null,
  reproduces_analysis_id: null,
}
const CALIBRATED = {
  analysis_id: 'c3d4e5f6a1b2',
  timestamp: '2026-11-07T09:03:00+00:00',
  participant_id: '0090005',
  atlas: 'cc200',
  run_id: '1bf121a5',
  prediction: 'control',
  confidence: 0.92,
  calibrated: true,
  git_commit: 'abc1234',
  reproduces_analysis_id: 'a1b2c3d4e5f6',
}
const RESPONSE = { total: 3, analyses: [NEWEST, MIDDLE, CALIBRATED] }

function renderPage() {
  return render(<History />)
}

describe('History page', () => {
  beforeEach(() => {
    vi.resetAllMocks()
  })

  it('shows the count and one row per analysis, newest first', async () => {
    getAnalyses.mockResolvedValue(RESPONSE)
    renderPage()

    expect(await screen.findByText('Showing 3 of 3 analyses, newest first.')).toBeInTheDocument()
    const rows = screen.getAllByRole('row')
    expect(rows).toHaveLength(4) // the header and three analyses
    expect(within(rows[1]).getByText('2026-11-07 09:05:00')).toBeInTheDocument()
    expect(within(rows[2]).getByText('2026-11-07 09:04:00')).toBeInTheDocument()
    expect(within(rows[3]).getByText('2026-11-07 09:03:00')).toBeInTheDocument()
    expect(within(rows[2]).getByText('Harvard-Oxford')).toBeInTheDocument()
    expect(
      screen.getByRole('columnheader', { name: 'Confidence in this prediction' }),
    ).toBeInTheDocument()
  })

  it('marks a confidence as not calibrated unless the record says calibrated', async () => {
    getAnalyses.mockResolvedValue(RESPONSE)
    renderPage()
    await screen.findByText('Showing 3 of 3 analyses, newest first.')

    const rows = screen.getAllByRole('row')
    expect(within(rows[1]).getByText('70.0%')).toBeInTheDocument()
    expect(within(rows[1]).getByText('(not calibrated)')).toBeInTheDocument()
    expect(within(rows[3]).getByText('92.0%')).toBeInTheDocument()
    expect(within(rows[3]).queryByText('(not calibrated)')).not.toBeInTheDocument()
  })

  it('sends the participant and atlas filters to the API, and Reset clears them', async () => {
    const user = userEvent.setup()
    getAnalyses.mockImplementation(async (params) =>
      params.atlas === 'cc200' ? { total: 1, analyses: [NEWEST] } : RESPONSE,
    )
    renderPage()
    await screen.findByText('Showing 3 of 3 analyses, newest first.')
    expect(getAnalyses).toHaveBeenCalledWith({ participant_id: '', atlas: '' })

    await user.type(screen.getByLabelText('Participant'), '50003')
    await user.selectOptions(screen.getByLabelText('Atlas'), 'cc200')
    await user.click(screen.getByRole('button', { name: 'Apply filters' }))

    expect(await screen.findByText('Showing 1 of 1 analyses, newest first.')).toBeInTheDocument()
    expect(getAnalyses).toHaveBeenLastCalledWith({ participant_id: '50003', atlas: 'cc200' })

    await user.click(screen.getByRole('button', { name: 'Reset filters' }))
    expect(await screen.findByText('Showing 3 of 3 analyses, newest first.')).toBeInTheDocument()
    expect(getAnalyses).toHaveBeenLastCalledWith({ participant_id: '', atlas: '' })
  })

  it('says so when no analysis has been run yet', async () => {
    getAnalyses.mockResolvedValue({ total: 0, analyses: [] })
    renderPage()

    expect(await screen.findByText('No analyses have been run yet.')).toBeInTheDocument()
    expect(screen.queryByRole('table')).not.toBeInTheDocument()
  })

  it('says so when no analysis matches the filters', async () => {
    const user = userEvent.setup()
    getAnalyses.mockImplementation(async (params) =>
      params.atlas === 'aal' ? { total: 0, analyses: [] } : RESPONSE,
    )
    renderPage()
    await screen.findByText('Showing 3 of 3 analyses, newest first.')

    await user.selectOptions(screen.getByLabelText('Atlas'), 'aal')
    await user.click(screen.getByRole('button', { name: 'Apply filters' }))

    expect(await screen.findByText('No analyses match these filters.')).toBeInTheDocument()
    expect(screen.queryByRole('table')).not.toBeInTheDocument()
  })

  it('opens one record with its ten fields and closes it again', async () => {
    const user = userEvent.setup()
    getAnalyses.mockResolvedValue(RESPONSE)
    getAnalysis.mockResolvedValue(NEWEST)
    renderPage()

    await user.click(await screen.findByRole('button', { name: 'Open analysis a1b2c3d4e5f6' }))
    expect(getAnalysis).toHaveBeenCalledWith('a1b2c3d4e5f6')

    const panel = await screen.findByRole('region', { name: 'Analysis record' })
    expect(await within(panel).findByText('not recorded')).toBeInTheDocument()
    for (const label of [
      'Analysis ID',
      'Time (UTC)',
      'Participant',
      'Atlas',
      'Run ID',
      'Prediction',
      'Confidence in this prediction',
      'Calibrated',
      'Git commit',
      'Reproduces analysis',
    ]) {
      expect(within(panel).getByText(label)).toBeInTheDocument()
    }
    expect(within(panel).getByText('a1b2c3d4e5f6')).toBeInTheDocument()
    expect(within(panel).getByText('2026-11-07 09:05:00')).toBeInTheDocument()
    expect(within(panel).getByText('CC200')).toBeInTheDocument()
    expect(within(panel).getByText('70.0% (not calibrated)')).toBeInTheDocument()
    expect(within(panel).getByText('no')).toBeInTheDocument()
    expect(within(panel).getByText('none (original analysis)')).toBeInTheDocument()

    await user.click(within(panel).getByRole('button', { name: 'Close' }))
    expect(screen.queryByRole('region', { name: 'Analysis record' })).not.toBeInTheDocument()
  })

  it('shows the git commit and the analysis a record reproduces', async () => {
    const user = userEvent.setup()
    getAnalyses.mockResolvedValue(RESPONSE)
    getAnalysis.mockResolvedValue(CALIBRATED)
    renderPage()

    await user.click(await screen.findByRole('button', { name: 'Open analysis c3d4e5f6a1b2' }))

    const panel = await screen.findByRole('region', { name: 'Analysis record' })
    expect(await within(panel).findByText('abc1234')).toBeInTheDocument()
    expect(within(panel).getByText('a1b2c3d4e5f6')).toBeInTheDocument()
    expect(within(panel).getByText('92.0% (calibrated)')).toBeInTheDocument()
    expect(within(panel).getByText('yes')).toBeInTheDocument()
  })

  it('shows the API error in plain words when a record cannot be opened', async () => {
    const user = userEvent.setup()
    getAnalyses.mockResolvedValue(RESPONSE)
    getAnalysis.mockRejectedValue(new Error('No analysis with that ID.'))
    renderPage()

    await user.click(await screen.findByRole('button', { name: 'Open analysis a1b2c3d4e5f6' }))

    const message = await screen.findByText(/Could not load this record/)
    expect(message).toHaveTextContent('No analysis with that ID.')
  })

  it('shows the API error in plain words instead of a table', async () => {
    getAnalyses.mockRejectedValue(
      new Error('The API is not reachable. Check that the server is running.'),
    )
    renderPage()

    const message = await screen.findByText(/Could not load analyses/)
    expect(message).toHaveTextContent('The API is not reachable. Check that the server is running.')
    expect(screen.queryByRole('table')).not.toBeInTheDocument()
  })
})