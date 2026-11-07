// The result of one analysis: the record of memo 0013, shown by the rules of memo 0012.
// Confidence is the probability of the predicted class (0.5 to 1), not of autism (memo 0006).
export default function ResultCard({ record }) {
  const percent = `${(record.confidence * 100).toFixed(1)}%`

  return (
    <article className="result-card" aria-label="Analysis result">
      <h2>Result</h2>
      <p className="result-prediction">
        Prediction: <strong>{record.prediction}</strong>
      </p>
      <dl className="result-details">
        <dt>Confidence in this prediction</dt>
        <dd>
          {percent}{' '}
          <span className={`badge ${record.calibrated ? 'badge-calibrated' : 'badge-uncalibrated'}`}>
            {record.calibrated ? 'calibrated' : 'not calibrated'}
          </span>
        </dd>
        <dt>Participant</dt>
        <dd>{record.participant_id}</dd>
        <dt>Atlas</dt>
        <dd>{record.atlas}</dd>
        <dt>Run ID</dt>
        <dd>{record.run_id}</dd>
        <dt>Analysis ID</dt>
        <dd>{record.analysis_id}</dd>
        <dt>Time (UTC)</dt>
        <dd>{record.timestamp}</dd>
      </dl>
    </article>
  )
}