import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import Explanation from './Explanation.jsx'
import Reliability from './Reliability.jsx'

describe('Planned pages', () => {
  it('Explanation says it is planned for FYP-II', () => {
    render(<Explanation />)
    expect(screen.getByRole('heading', { name: 'Explanation' })).toBeInTheDocument()
    expect(screen.getByText(/Planned for FYP-II/)).toBeInTheDocument()
  })

  it('Reliability says it is planned for FYP-II', () => {
    render(<Reliability />)
    expect(screen.getByRole('heading', { name: 'Reliability' })).toBeInTheDocument()
    expect(screen.getByText(/Planned for FYP-II/)).toBeInTheDocument()
  })
})