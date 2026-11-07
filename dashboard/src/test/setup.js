// Runs before every test file (W5-16).
import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { afterEach } from 'vitest'

// Remove what the last test drew on the page, so tests cannot affect each other.
afterEach(() => {
  cleanup()
})