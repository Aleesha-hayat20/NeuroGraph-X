import { expect, test } from '@playwright/test'

// W6-13: the main use case in a real browser, on the fixture dataset (memo 0014):
// select a participant, choose an atlas, run, see the result, find it in History.
test('run an analysis and find it in History', async ({ page }) => {
  await page.goto('/participants')
  // Safety check: this test must only ever run on the synthetic dataset.
  await expect(page.getByText('Fixture data').first()).toBeVisible()

  // Select a participant with Run, which opens the Analysis page with that participant.
  const row = page.getByRole('row').filter({ hasText: '0090001' })
  await row.getByRole('button', { name: 'Run' }).click()
  await expect(page).toHaveURL(/\/analysis\?participant=0090001/)
  await expect(page.getByLabel('Participant')).toHaveValue('0090001')

  // Choose an atlas and run.
  await page.getByLabel('CC200').check()
  await page.getByRole('button', { name: 'Run analysis' }).click()

  // The result card shows the prediction, the confidence label and the analysis ID.
  const result = page.getByRole('article', { name: 'Analysis result' })
    // The first analysis loads PyTorch and the model, so it can take a while on a cold start.
  await expect(result).toBeVisible({ timeout: 120_000 })
  await expect(result.getByText('Prediction:')).toBeVisible()
  await expect(result.getByText('Confidence in this prediction')).toBeVisible()
  const analysisId = (await result.locator('dt:text-is("Analysis ID") + dd').textContent()).trim()
  expect(analysisId).toMatch(/^[0-9a-f]{12}$/)

  // The same analysis is in History and opens as a full record.
  await page.getByRole('link', { name: 'History' }).click()
  await expect(page).toHaveURL(/\/history/)
  await page.getByRole('button', { name: `Open analysis ${analysisId}` }).click()
  const record = page.getByRole('region', { name: 'Analysis record' })
  await expect(record.getByRole('heading', { name: `Analysis ${analysisId}` })).toBeVisible()
  await expect(record.locator('dd', { hasText: analysisId })).toBeVisible()
  await expect(record.locator('dd', { hasText: '0090001' })).toBeVisible()
})