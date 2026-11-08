import { useEffect, useState } from 'react'
import { getModels } from '../api/client.js'

// Models page (W6-11): for each atlas the registered model, its cross-validation and
// frozen-set results, and the effect of calibration (memo 0010): ECE before and after, and a
// reliability diagram. Everything comes from GET /models (memo 0013); the page computes nothing.
const ATLAS_LABELS = {
  aal: 'AAL',
  cc200: 'CC200',
  ho: 'Harvard-Oxford',
  dosenbach160: 'Dosenbach 160',
}

function atlasLabel(key) {
  return ATLAS_LABELS[key] ?? key
}

function percent(value) {
  return typeof value === 'number' ? `${(value * 100).toFixed(1)}%` : 'not recorded'
}

function decimal(value, digits = 3) {
  return typeof value === 'number' ? value.toFixed(digits) : 'not recorded'
}

function cvText(cv) {
  if (!cv || typeof cv.mean !== 'number') return 'not recorded'
  return typeof cv.sd === 'number'
    ? `${percent(cv.mean)} ± ${(cv.sd * 100).toFixed(1)}`
    : percent(cv.mean)
}

// Reliability diagram: predicted probability against observed share, one point per bin that
// has participants. The dashed grey diagonal is perfect calibration.
const SIZE = 260
const PAD = 38
const INNER = SIZE - 2 * PAD
const TICKS = [0, 0.5, 1]

function px(value) {
  return PAD + value * INNER
}

function py(value) {
  return SIZE - PAD - value * INNER
}

function Series({ bins, name }) {
  const shown = bins.filter((bin) => bin.n > 0)
  const points = shown.map((bin) => `${px(bin.mean_prob)},${py(bin.observed)}`).join(' ')
  return (
    <>
      <polyline className={`rel-${name}`} points={points} fill="none" />
      {shown.map((bin) => (
        <circle
          key={bin.lower}
          className={`rel-${name}-dot`}
          cx={px(bin.mean_prob)}
          cy={py(bin.observed)}
          r="3"
        />
      ))}
    </>
  )
}

function ReliabilityDiagram({ atlas, before, after }) {
  return (
    <svg
      className="reliability"
      viewBox={`0 0 ${SIZE} ${SIZE}`}
      role="img"
      aria-label={`Reliability diagram for ${atlasLabel(atlas)}, before and after calibration`}
    >
      <rect className="rel-frame" x={PAD} y={PAD} width={INNER} height={INNER} />
      <line className="rel-diagonal" x1={px(0)} y1={py(0)} x2={px(1)} y2={py(1)} />
      <Series bins={before} name="before" />
      <Series bins={after} name="after" />
      {TICKS.map((tick) => (
        <text key={`x${tick}`} className="rel-tick" x={px(tick)} y={SIZE - PAD + 14} textAnchor="middle">
          {tick}
        </text>
      ))}
      {TICKS.map((tick) => (
        <text key={`y${tick}`} className="rel-tick" x={PAD - 6} y={py(tick) + 3} textAnchor="end">
          {tick}
        </text>
      ))}
      <text className="rel-label" x={SIZE / 2} y={SIZE - 4} textAnchor="middle">
        Predicted probability of autism
      </text>
      <text className="rel-label" x="12" y={SIZE / 2} textAnchor="middle" transform={`rotate(-90 12 ${SIZE / 2})`}>
        Observed share with autism
      </text>
    </svg>
  )
}

function ModelCard({ model }) {
  const label = atlasLabel(model.atlas)
  const oof = model.calibration?.oof
  const drawn = model.calibrated && oof?.reliability_before && oof?.reliability_after
  return (
    <section className="model-card" aria-label={`${label} model`}>
      <h2>{label}</h2>
      {drawn ? (
        <>
          <ReliabilityDiagram
            atlas={model.atlas}
            before={oof.reliability_before}
            after={oof.reliability_after}
          />
          <p className="muted">
            ECE {decimal(oof.before?.ece)} before, {decimal(oof.after_cross_fitted?.ece)} after
            (out-of-fold predictions, {model.calibration.n} participants; {model.calibration.method}{' '}
            scaling).
          </p>
        </>
      ) : (
        <p className="muted">Not calibrated: no reliability diagram.</p>
      )}
      {!model.checkpoint_available && (
        <p className="muted">The model file is not on this machine, so it cannot run analyses here.</p>
      )}
    </section>
  )
}

export default function Models() {
  const [state, setState] = useState({ status: 'loading' })

  useEffect(() => {
    let cancelled = false
    getModels()
      .then((models) => {
        if (!cancelled) setState({ status: 'ok', models })
      })
      .catch((error) => {
        if (!cancelled) setState({ status: 'error', message: error.message })
      })
    return () => {
      cancelled = true
    }
  }, [])

  if (state.status === 'loading') {
    return (
      <section>
        <h1>Models</h1>
        <p className="muted">Loading models...</p>
      </section>
    )
  }

  if (state.status === 'error') {
    return (
      <section>
        <h1>Models</h1>
        <p className="api-error">Could not load the models. {state.message}</p>
      </section>
    )
  }

  const { models } = state
  if (models.length === 0) {
    return (
      <section>
        <h1>Models</h1>
        <p className="muted">No models are registered.</p>
      </section>
    )
  }

  return (
    <section>
      <h1>Models</h1>
      <p className="muted">
        The registered model of each atlas: cross-validation and frozen-set results, and the effect
        of calibration (memo 0010).
      </p>

      <div className="table-wrap">
        <table className="data-table">
          <thead>
            <tr>
              <th>Atlas</th>
              <th>Run</th>
              <th>CV accuracy (5-fold)</th>
              <th>Frozen accuracy</th>
              <th>Frozen AUC</th>
              <th>ECE before calibration</th>
              <th>ECE after calibration</th>
            </tr>
          </thead>
          <tbody>
            {models.map((model) => {
              const frozen = model.metrics?.frozen
              const calibration = model.calibrated ? model.calibration?.frozen : null
              return (
                <tr key={model.atlas}>
                  <td>{atlasLabel(model.atlas)}</td>
                  <td>{model.run_id}</td>
                  <td>{cvText(model.metrics?.cv_accuracy)}</td>
                  <td>{percent(frozen?.accuracy)}</td>
                  <td>{decimal(frozen?.auc)}</td>
                  <td>{calibration ? decimal(calibration.before?.ece) : 'not calibrated'}</td>
                  <td>{calibration ? decimal(calibration.after?.ece) : 'not calibrated'}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
      <p className="muted">
        Frozen set: 100 held-out participants, measured once. ECE is the expected calibration
        error, lower is better, measured on the frozen set.
      </p>

      <h2>Reliability diagrams</h2>
      <p className="muted">
        Dashed line: before calibration. Solid line: after calibration. Dotted grey diagonal:
        perfect calibration.
      </p>
      <div className="model-grid">
        {models.map((model) => (
          <ModelCard key={model.atlas} model={model} />
        ))}
      </div>
    </section>
  )
}