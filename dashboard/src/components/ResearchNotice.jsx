// Shown on every page through the layout (memo 0012, display rules).
// The proposal requires this statement in the interface itself, not only in documentation.
export default function ResearchNotice() {
  return (
    <p className="research-notice" role="note">
      <strong>Research use only.</strong> NeuroGraph-X is a research analysis tool. It does
      not diagnose, and it is not a medical device.
    </p>
  )
}
