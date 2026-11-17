import { render, screen, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { getCohortSummary } from '../api/client.js'
import Overview from './Overview.jsx'

// The page is tested without a server: the API client is replaced by a stand-in.
vi.mock('../api/client.js', () => ({ getCohortSummary: vi.fn() }))

// Invented counts in the shape of GET /cohort/summary (memo 0013). Every breakdown
// adds up to the totals: 7 included, 3 excluded.
const SUMMARY = {
  total: 10,
  included: 7,
  excluded: 3,
  excluded_by_gate: { rater: 2, motion: 1, completeness: 0 },
  by_group: {
    autism: { included: 4, excluded: 2 },
    control: { included: 3, excluded: 1 },
  },
  by_site: [
    { site: 'SYN_A', included: 4, excluded: 1 },
    { site: 'SYN_B', included: 3, excluded: 2 },
  ],
  by_split: { frozen: 2, development: 5 },
}

function renderPage() {
  return render(
    <MemoryRouter>
      <Overview />
    </MemoryRouter>,
  )
}

describe('Overview page', () => {
  beforeEach(() => {
    getCohortSummary.mockReset()
  })

  it('shows the totals, gate counts and split counts', async () => {
    getCohortSummary.mockResolvedValue(SUMMARY)
    renderPage()

    expect(
      await screen.findByText('10 participants: 7 included, 3 excluded by quality control.'),
    ).toBeInTheDocument()

    const gates = screen.getByRole('table', { name: 'Excluded, by first gate failed' })
    expect(within(gates).getByRole('row', { name: /Rater\s*2/ })).toBeInTheDocument()
    expect(within(gates).getByRole('row', { name: /Motion\s*1/ })).toBeInTheDocument()
    expect(within(gates).getByRole('row', { name: /Completeness\s*0/ })).toBeInTheDocument()

    const splits = screen.getByRole('table', { name: 'Included, by split' })
    expect(within(splits).getByRole('row', { name: /Frozen evaluation set\s*2/ })).toBeInTheDocument()
    expect(within(splits).getByRole('row', { name: /Development\s*5/ })).toBeInTheDocument()
  })

  it('draws one bar per group and per site with the right counts', async () => {
    getCohortSummary.mockResolvedValue(SUMMARY)
    renderPage()

    expect(await screen.findByRole('img', { name: 'Autism: 4 included, 2 excluded' })).toBeInTheDocument()
    expect(screen.getByRole('img', { name: 'Control: 3 included, 1 excluded' })).toBeInTheDocument()
    expect(screen.getByRole('img', { name: 'SYN_A: 4 included, 1 excluded' })).toBeInTheDocument()
    expect(screen.getByRole('img', { name: 'SYN_B: 3 included, 2 excluded' })).toBeInTheDocument()
  })

  it('links to the exclusion log', async () => {
    getCohortSummary.mockResolvedValue(SUMMARY)
    renderPage()

    const link = await screen.findByRole('link', { name: /every excluded participant/i })
    expect(link).toHaveAttribute('href', '/exclusions')
  })

  it('says so while loading', () => {
    getCohortSummary.mockReturnValue(new Promise(() => {}))
    renderPage()

    expect(screen.getByText(/Loading cohort summary/)).toBeInTheDocument()
  })

  it('says so when there are no participants', async () => {
    getCohortSummary.mockResolvedValue({
      ...SUMMARY,
      total: 0,
      included: 0,
      excluded: 0,
    })
    renderPage()

    expect(await screen.findByText('No participants found.')).toBeInTheDocument()
  })

  it('shows the error when the API fails', async () => {
    getCohortSummary.mockRejectedValue(new Error('API offline'))
    renderPage()

    expect(await screen.findByText(/Could not load the cohort summary/)).toBeInTheDocument()
    expect(screen.getByText(/API offline/)).toBeInTheDocument()
  })
})