// Display formats shared by the pages, so the same value reads the same everywhere (W7-19).

// The atlas keys the API accepts, with the names used elsewhere in the project.
export const ATLASES = [
  { key: 'aal', label: 'AAL' },
  { key: 'cc200', label: 'CC200' },
  { key: 'ho', label: 'Harvard-Oxford' },
  { key: 'dosenbach160', label: 'Dosenbach 160' },
]

export function atlasLabel(key) {
  const found = ATLASES.find((atlas) => atlas.key === key)
  return found ? found.label : key
}

// 2026-11-17T14:39:21+00:00 -> 2026-11-17 14:39:21 (UTC, as the column headers say)
export function formatTime(timestamp) {
  return timestamp.slice(0, 19).replace('T', ' ')
}

// 1112 -> 1,112
export function formatCount(count) {
  return count.toLocaleString('en-US')
}