import { render, screen, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { getModels } from '../api/client.js'
import Models from './Models.jsx'

// The page is tested without a server: the API client is replaced by a stand-in.
vi.mock('../api/client.js', () => ({ getModels: vi.fn() }))

// Invented models in the shape of GET /models (memo 0013), not real results.
const BINS_BEFORE = [
  { lower: 0, upper: 0.5, n: 10, mean_prob: 0.25, observed: 0.4 },
  { lower: 0.5, upper: 1, n: 20, mean_prob: 0.75, observed: 0.6 },
]
const BINS_AFTER = [
  { lower: 0, upper: 0.5, n: 12, mean_prob: 0.3, observed: 0.35 },
  { lower: 0.5, upper: 1, n: 18, mean_prob: 0.7, observed: 0.65 },
]
const CALIBRATED = {
  atlas: 'aal',
  run_id: 'aaaa1111',
  checkpoint_available: false,
  metrics: { cv_accuracy: { mean: 0.7, sd: 0.02 }, frozen: { accuracy: 0.65, auc: 0.7 } },
  calibrated: true,
  calibration: {
    method: 'platt',
    n: 761,
    oof: {
      before: { ece: 0.17 },
      after_cross_fitted: { ece: 0.08 },
      reliability_before: BINS_BEFORE,
      reliability_after: BINS_AFTER,
    },
    frozen: { before: { ece: 0.25 }, after: { ece: 0.1 } },
  },
}
const UNCALIBRATED = {
  atlas: 'cc200',
  run_id: 'bbbb2222',
  checkpoint_available: true,
  metrics: { cv_accuracy: { mean: 0.6, sd: 0.03 }, frozen: { accuracy: 0.55, auc: 0.6 } },
  calibrated: false,
  calibration: null,
}

describe('Models page', () => {
  beforeEach(() => {
    vi.resetAllMocks()
  })

  it('shows one row per atlas with its cross-validation, frozen and ECE results', async () => {
    getModels.mockResolvedValue([CALIBRATED, UNCALIBRATED])
    render(<Models />)

    expect(await screen.findByText('aaaa1111')).toBeInTheDocument()
    const rows = screen.getAllByRole('row')
    expect(rows).toHaveLength(3) // the header and two atlases
    for (const text of ['AAL', '70.0% ± 2.0', '65.0%', '0.700', '0.250', '0.100']) {
      expect(within(rows[1]).getByText(text)).toBeInTheDocument()
    }
  })

  it('says not calibrated, and draws no diagram, for a model without calibration', async () => {
    getModels.mockResolvedValue([CALIBRATED, UNCALIBRATED])
    render(<Models />)

    await screen.findByText('bbbb2222')
    const row = screen.getAllByRole('row')[2]
    expect(within(row).getAllByText('not calibrated')).toHaveLength(2)
    expect(screen.getByText('Not calibrated: no reliability diagram.')).toBeInTheDocument()
    expect(screen.queryByRole('img', { name: /CC200/ })).not.toBeInTheDocument()
  })

  it('draws the reliability diagram and the ECE before and after for a calibrated model', async () => {
    getModels.mockResolvedValue([CALIBRATED, UNCALIBRATED])
    render(<Models />)

    expect(
      await screen.findByRole('img', { name: 'Reliability diagram for AAL, before and after calibration' }),
    ).toBeInTheDocument()
    expect(screen.getByText(/ECE 0\.170 before, 0\.080 after/)).toBeInTheDocument()
    expect(screen.getByText(/761 participants; platt scaling/)).toBeInTheDocument()
  })

  it('says when a model file is not on this machine', async () => {
    getModels.mockResolvedValue([CALIBRATED, UNCALIBRATED])
    render(<Models />)

    const aal = await screen.findByRole('region', { name: 'AAL model' })
    expect(within(aal).getByText(/model file is not on this machine/)).toBeInTheDocument()
    const cc200 = screen.getByRole('region', { name: 'CC200 model' })
    expect(within(cc200).queryByText(/model file is not on this machine/)).not.toBeInTheDocument()
  })

  it('says so when no model is registered', async () => {
    getModels.mockResolvedValue([])
    render(<Models />)

    expect(await screen.findByText('No models are registered.')).toBeInTheDocument()
    expect(screen.queryByRole('table')).not.toBeInTheDocument()
  })

  it('shows the API error in plain words instead of a table', async () => {
    getModels.mockRejectedValue(new Error('The API is not reachable. Check that the server is running.'))
    render(<Models />)

    const message = await screen.findByText(/Could not load the models/)
    expect(message).toHaveTextContent('The API is not reachable. Check that the server is running.')
    expect(screen.queryByRole('table')).not.toBeInTheDocument()
  })
})