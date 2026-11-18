import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { exportUrl, getAnalyses, getAnalysis, regenerateAnalysis } from '../api/client.js'
import History from './History.jsx'

// The page is tested without a server: the API client is replaced by a stand-in.
vi.mock('../api/client.js', () => ({
  getAnalyses: vi.fn(),
  getAnalysis: vi.fn(),
  regenerateAnalysis: vi.fn(),
  exportUrl: vi.fn(),
}))

// Invented records in the shape of memo 0013: an original and its regenerated repeat.
const ORIGINAL = {
  analysis_id: 'a1b2c3d4e5f6',
  timestamp: '2026-11-07T09:05:00+00:00',
  participant_id: '0090001',
  atlas: 'cc200',
  run_id: '1bf121a5',
  prediction: 'control',
  confidence: 0.7,
  calibrated: true,
  git_commit: 'abc1234',
  reproduces_analysis_id: null,
}
const REPEAT = {
  ...ORIGINAL,
  analysis_id: 'f6e5d4c3b2a1',
  timestamp: '2026-11-07T09:10:00+00:00',
  reproduces_analysis_id: 'a1b2c3d4e5f6',
}

async function openOriginal(user) {
  render(<History />)
  await user.click(await screen.findByRole('button', { name: 'Open analysis a1b2c3d4e5f6' }))
  await screen.findByRole('button', { name: 'Regenerate' })
}

describe('History page: export and regenerate', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    getAnalyses.mockResolvedValue({ total: 1, analyses: [ORIGINAL] })
    getAnalysis.mockImplementation(async (id) => (id === ORIGINAL.analysis_id ? ORIGINAL : REPEAT))
    exportUrl.mockImplementation((id, format) => `/api/analyses/${id}/export?format=${format}`)
  })

  it('offers the open record as a JSON and a CSV download', async () => {
    await openOriginal(userEvent.setup())

    expect(screen.getByRole('link', { name: 'Export JSON' })).toHaveAttribute(
      'href',
      '/api/analyses/a1b2c3d4e5f6/export?format=json',
    )
    expect(screen.getByRole('link', { name: 'Export CSV' })).toHaveAttribute(
      'href',
      '/api/analyses/a1b2c3d4e5f6/export?format=csv',
    )
  })

  it('says the repeat is identical to the original', async () => {
    regenerateAnalysis.mockResolvedValue({
      analysis: REPEAT,
      original: ORIGINAL,
      identical: true,
      differences: [],
    })
    const user = userEvent.setup()
    await openOriginal(user)

    await user.click(screen.getByRole('button', { name: 'Regenerate' }))

    expect(await screen.findByText('Identical to the original.')).toBeInTheDocument()
    expect(regenerateAnalysis).toHaveBeenCalledWith('a1b2c3d4e5f6')
  })

  it('names the fields that differ', async () => {
    regenerateAnalysis.mockResolvedValue({
      analysis: { ...REPEAT, confidence: 0.6 },
      original: ORIGINAL,
      identical: false,
      differences: ['confidence'],
    })
    const user = userEvent.setup()
    await openOriginal(user)

    await user.click(screen.getByRole('button', { name: 'Regenerate' }))

    expect(
      await screen.findByText('Not identical to the original. Different: confidence.'),
    ).toBeInTheDocument()
  })

  it('opens the regenerated analysis from the result', async () => {
    regenerateAnalysis.mockResolvedValue({
      analysis: REPEAT,
      original: ORIGINAL,
      identical: true,
      differences: [],
    })
    const user = userEvent.setup()
    await openOriginal(user)
    await user.click(screen.getByRole('button', { name: 'Regenerate' }))

    await user.click(await screen.findByRole('button', { name: 'Open the new analysis' }))

    expect(getAnalysis).toHaveBeenCalledWith('f6e5d4c3b2a1')
  })

  it('shows the API message when the analysis cannot be regenerated', async () => {
    regenerateAnalysis.mockRejectedValue(
      new Error('The checkpoint of run 1bf121a5 is not available on this machine.'),
    )
    const user = userEvent.setup()
    await openOriginal(user)

    await user.click(screen.getByRole('button', { name: 'Regenerate' }))

    expect(await screen.findByText(/Could not regenerate this analysis/)).toBeInTheDocument()
    expect(screen.getByText(/checkpoint of run 1bf121a5 is not available/)).toBeInTheDocument()
  })

  it('links a regenerated record back to its original', async () => {
    getAnalyses.mockResolvedValue({ total: 1, analyses: [REPEAT] })
    const user = userEvent.setup()
    render(<History />)
    await user.click(await screen.findByRole('button', { name: 'Open analysis f6e5d4c3b2a1' }))

    await user.click(await screen.findByRole('button', { name: 'Open original analysis' }))

    expect(getAnalysis).toHaveBeenCalledWith('a1b2c3d4e5f6')
  })
})