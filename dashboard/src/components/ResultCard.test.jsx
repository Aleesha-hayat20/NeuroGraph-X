import { afterEach, describe, expect, it } from 'vitest'
import { cleanup, render, screen } from '@testing-library/react'
import ResultCard from './ResultCard.jsx'

// Invented test data, not a real analysis.
const RECORD = {
  analysis_id: 'a1b2c3d4e5f6',
  timestamp: '2026-11-07T09:00:00+00:00',
  participant_id: '0090001',
  atlas: 'cc200',
  run_id: '1bf121a5',
  prediction: 'autism',
  confidence: 0.81,
  calibrated: false,
}

afterEach(cleanup)

describe('ResultCard', () => {
  it('shows the prediction and the confidence in this prediction as a percentage', () => {
    render(<ResultCard record={RECORD} />)
    expect(screen.getByRole('article', { name: 'Analysis result' })).toBeTruthy()
    expect(screen.getByText('autism')).toBeTruthy()
    expect(screen.getByText('Confidence in this prediction')).toBeTruthy()
    expect(screen.getByText('81.0%')).toBeTruthy()
  })

  it('labels an uncalibrated confidence as not calibrated', () => {
    render(<ResultCard record={RECORD} />)
    expect(screen.getByText('not calibrated')).toBeTruthy()
    expect(screen.queryByText('calibrated')).toBeNull()
  })

  it('labels a calibrated confidence as calibrated', () => {
    render(<ResultCard record={{ ...RECORD, calibrated: true, confidence: 0.92 }} />)
    expect(screen.getByText('92.0%')).toBeTruthy()
    expect(screen.getByText('calibrated')).toBeTruthy()
    expect(screen.queryByText('not calibrated')).toBeNull()
  })

  it('shows participant, atlas, run, analysis ID and time', () => {
    render(<ResultCard record={RECORD} />)
    for (const text of ['0090001', 'cc200', '1bf121a5', 'a1b2c3d4e5f6', '2026-11-07T09:00:00+00:00']) {
      expect(screen.getByText(text)).toBeTruthy()
    }
  })
})