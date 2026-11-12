// The one place where the dashboard talks to the NeuroGraph-X REST API (memo 0012).
//
// Paths are relative to /api. In development and in `vite preview`, the Vite proxy
// (vite.config.js) forwards /api/... to the FastAPI server and removes the /api prefix,
// so the API needs no CORS setting and its routes stay as documented.
//
// Each issue adds its own function next to these, using request(). getAtlases and
// createAnalysis follow memo 0013 and work once those endpoints are merged on main.

const BASE = '/api'

/** An error from the API, or from not reaching it. `message` is plain language, safe to show. */
export class ApiError extends Error {
  constructor(status, message) {
    super(message)
    this.name = 'ApiError'
    this.status = status // 0 means the API could not be reached
  }
}

// FastAPI sends {"detail": "text"} for errors we raise and {"detail": [{"msg": ...}]} for 422.
function detailText(body, fallback) {
  const detail = body && body.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    const text = detail.map((item) => item.msg).filter(Boolean).join('; ')
    return text || fallback
  }
  return fallback
}

async function request(path, options = {}) {
  let response
  try {
    response = await fetch(`${BASE}${path}`, options)
  } catch {
    throw new ApiError(0, 'The API is not reachable. Check that the server is running.')
  }

  let body = null
  try {
    body = await response.json()
  } catch {
    // empty or non-JSON body: handled below
  }

  if (!response.ok) {
    // The dev proxy answers 502 or 504 with no body when nothing is listening behind it.
    // An error the API itself raised always carries a `detail`, so no detail means no API.
    const hasDetail = body && body.detail
    if (!hasDetail && (response.status === 502 || response.status === 504)) {
      throw new ApiError(0, 'The API is not reachable. Check that the server is running.')
    }
    throw new ApiError(
      response.status,
      detailText(body, `The API returned an error (${response.status}).`),
    )
  }
  return body
}

function withQuery(path, params = {}) {
  const query = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== '') query.set(key, value)
  }
  const text = query.toString()
  return text ? `${path}?${text}` : path
}

/** GET /health -> { status, version, participant_table_found, data_mode } where data_mode is "real" or "fixtures" */
export function getHealth() {
  return request('/health')
}

/**
 * GET /participants -> { total, included, excluded, participants: [...] }
 * `params.qc_status` may be "included" or "excluded".
 */
export function getParticipants(params = {}) {
  return request(withQuery('/participants', params))
}

/**
 * GET /exclusions -> { total, exclusions: [...] }, one entry per excluded participant:
 * { participant_id, file_id, site, group, first_gate_failed, gates_failed, reasons }.
 * `params.gate` ("rater", "motion" or "completeness") keeps those whose first failed gate it is.
 */
export function getExclusions(params = {}) {
  return request(withQuery('/exclusions', params))
}

/**
 * GET /analyses -> { total, analyses: [...] }, newest first.
 * `params.participant_id` (0050003 or 50003), `params.atlas` and `params.limit` (default 50)
 * are all optional. `total` counts every match, `analyses` holds at most `limit` of them.
 */
export function getAnalyses(params = {}) {
  return request(withQuery('/analyses', params))
}

/** GET /analyses/{analysis_id} -> one analysis record with the ten fields of memo 0013. */
export function getAnalysis(analysisId) {
  return request(`/analyses/${encodeURIComponent(analysisId)}`)
}

/**
 * GET /atlases -> [{ atlas, label, n_regions, data_available, model_registered, run_id }, ...]
 * All four atlases are listed, whether or not a model exists for them (memo 0013).
 */
export function getAtlases() {
  return request('/atlases')
}

/**
 * POST /analyses with { participant_id, atlas } -> 201 and the analysis record (memo 0013):
 * { analysis_id, timestamp, participant_id, atlas, run_id, prediction, confidence,
 *   calibrated, git_commit, reproduces_analysis_id }
 * Errors carry a plain-language `detail`: 404 unknown participant, 409 excluded,
 * 422 unknown atlas, 503 no connectomes or no model.
 */
export function createAnalysis(participantId, atlas) {
  return request('/analyses', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ participant_id: participantId, atlas }),
  })
}


/**
 * GET /models -> one entry per registered atlas model: { atlas, run_id, registered_at,
 * checkpoint_available, hyperparameters, metrics, calibrated, calibration, ... } (memo 0013).
 */
export function getModels() {
  return request('/models')
}