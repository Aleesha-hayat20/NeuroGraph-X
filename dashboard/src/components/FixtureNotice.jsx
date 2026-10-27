// Shown on every page while the API runs on the fixture dataset (memo 0012, memo 0014).
// It keeps a screenshot of fixture output from being mistaken for a real result.
export default function FixtureNotice() {
  return (
    <p className="fixture-notice" role="status">
      <strong>Fixture data.</strong> The API is running on a small synthetic dataset for testing
      the software. Nothing shown here is a real result, and none of it may be reported.
    </p>
  )
}
