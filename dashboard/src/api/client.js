// The one place where the dashboard talks to the NeuroGraph-X REST API (memo 0012).
//
// Paths are relative to /api. In development and in `vite preview`, the Vite proxy
// (vite.config.js) forwards /api/... to the FastAPI server and removes the /api prefix,
// so the API needs no CORS setting and its routes stay as documented.
//
// Only the endpoints that exist on main today are here. Each later issue adds its own
// function next to these (GET /atlases, POST /analyses, GET /models, ...), using request().

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

/** GET /health -> { status, version, participant_table_found } */
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
