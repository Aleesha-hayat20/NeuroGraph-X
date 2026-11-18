import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useHealth } from '../api/useHealth.js'
import About from './About.jsx'

// The page is tested without a server: the health hook is replaced by a stand-in.
vi.mock('../api/useHealth.js', () => ({ useHealth: vi.fn() }))

describe('About page', () => {
  beforeEach(() => {
    useHealth.mockReset()
  })

  it('shows the research-use statement, the team and the API version', () => {
    useHealth.mockReturnValue({
      state: 'ok',
      health: { status: 'ok', version: '9.9.9', data_mode: 'fixtures' },
    })
    render(<About />)

    expect(screen.getByText(/does not diagnose, and it is not a medical device/)).toBeInTheDocument()
    expect(screen.getByText('Aleesha Hayat')).toBeInTheDocument()
    expect(screen.getByText('Laiba Afridi')).toBeInTheDocument()
    expect(screen.getByText('Alishba Fayaz')).toBeInTheDocument()
    expect(screen.getByText('API version 9.9.9, data mode: fixtures.')).toBeInTheDocument()
  })

  it('says so when the API cannot be reached', () => {
    useHealth.mockReturnValue({ state: 'error', message: 'API not reachable' })
    render(<About />)

    expect(screen.getByText(/API not reachable/)).toBeInTheDocument()
  })
})