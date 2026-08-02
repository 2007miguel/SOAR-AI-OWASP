const BASE = 'http://localhost:8000/api/v1'

async function _handleResponse(res) {
  if (!res.ok) {
    let err
    try { err = await res.json() } catch { err = { detail: `HTTP ${res.status}` } }
    throw err
  }
  return res.json()
}

export async function createAssessment(payload) {
  const res = await fetch(`${BASE}/assessments`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  return _handleResponse(res)
}

export async function submitAttest(assessmentId, payload) {
  const res = await fetch(`${BASE}/assessments/${assessmentId}/attest`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  return _handleResponse(res)
}

export async function getAssessment(assessmentId) {
  const res = await fetch(`${BASE}/assessments/${assessmentId}`)
  return _handleResponse(res)
}
