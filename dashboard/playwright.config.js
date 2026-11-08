import process from 'node:process'
import { defineConfig, devices } from '@playwright/test'

// End-to-end test (W6-13): a real browser drives the dashboard, which talks to a real API
// server running on the synthetic fixture dataset (memo 0014). Both servers are started here,
// and an already running server is never reused, so the test cannot reach the real data.
//
// The API needs Python with the project installed. Locally set NGX_PYTHON to the python of
// the virtual environment; in CI the installed python is used.
const python = process.env.NGX_PYTHON ?? 'python'

export default defineConfig({
  testDir: 'e2e',
  testMatch: '**/*.e2e.js',
  timeout: 180_000,
  expect: { timeout: 30_000 },
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [['list'], ['html', { open: 'never' }]] : 'list',
  use: { baseURL: 'http://127.0.0.1:5173', trace: 'retain-on-failure' },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: [
    {
      command: `${python} -m uvicorn neurographx.api.main:app --host 127.0.0.1 --port 8000`,
      cwd: '..',
      url: 'http://127.0.0.1:8000/health',
      env: { NGX_DATA: 'fixtures' },
      reuseExistingServer: false,
      timeout: 120_000,
    },
    {
      command: 'npm run dev -- --host 127.0.0.1 --port 5173 --strictPort',
      url: 'http://127.0.0.1:5173',
      reuseExistingServer: false,
      timeout: 120_000,
    },
  ],
})