import { useState } from 'react'
import { submitAttest } from '../api'
import AttestRow from './AttestRow'
import GlobalFlags from './GlobalFlags'

const INITIAL_GLOBAL = {
  incident_response_plan: false,
  red_teaming_done: false,
  red_teaming_critical_findings: false,
  supply_chain_unverified: false,
  production_access: false,
  assurance_methods_used: [],
  _methods_raw: '',
}

function buildInitialAtts(checklist) {
  return Object.fromEntries(
    checklist.map(item => [item.control_id, { status: '', evidence: '' }])
  )
}

export default function ChecklistPanel({ assessmentId, checklist }) {
  const [atts, setAtts] = useState(() => buildInitialAtts(checklist))
  const [globalFlags, setGlobalFlags] = useState(INITIAL_GLOBAL)
  const [submitting, setSubmitting] = useState(false)
  const [lastResult, setLastResult] = useState(null)
  const [error, setError] = useState(null)

  const filledCount = Object.values(atts).filter(v => v.status !== '').length
  const isReady = lastResult?.is_ready ?? false

  function handleAttChange(controlId, next) {
    setAtts(prev => ({ ...prev, [controlId]: next }))
  }

  async function handleSubmit() {
    setSubmitting(true)
    setError(null)

    const attestations = {}
    for (const [ctrl_id, val] of Object.entries(atts)) {
      if (val.status) {
        attestations[ctrl_id] = {
          status: val.status,
          evidence: val.evidence || undefined,
        }
      }
    }

    const { _methods_raw: _r, ...globalClean } = globalFlags

    const payload = {
      attestations,
      ...globalClean,
    }

    try {
      const result = await submitAttest(assessmentId, payload)
      setLastResult(result)
    } catch (e) {
      setError(e.detail || JSON.stringify(e))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div>
      <div className="card">
        <h2>
          Checklist de Aseguramiento — {checklist.length} controles requeridos
        </h2>
        <p className="hint mb">
          Puedes enviar en múltiples rondas. Solo se actualizan los controles que tengan estado seleccionado.
          El veredicto se emite automáticamente cuando todos los controles críticos están cubiertos.
        </p>

        <div style={{ overflowX: 'auto' }}>
          <table className="checklist-table">
            <thead>
              <tr>
                <th>Control</th>
                <th>ASIs</th>
                <th>Amenazas</th>
                <th>Categoría</th>
                <th>Métodos sugeridos</th>
                <th>Estado</th>
                <th>Evidencia</th>
              </tr>
            </thead>
            <tbody>
              {checklist.map(item => (
                <AttestRow
                  key={item.control_id}
                  item={item}
                  value={atts[item.control_id]}
                  onChange={next => handleAttChange(item.control_id, next)}
                />
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="card">
        <h2>Flags Globales y Señales M7</h2>
        <GlobalFlags values={globalFlags} onChange={setGlobalFlags} />
      </div>

      <div className="flex-row mt">
        <button
          className="btn-primary"
          onClick={handleSubmit}
          disabled={submitting}
        >
          {submitting
            ? 'Enviando...'
            : `Enviar attestaciones (${filledCount}/${checklist.length} completadas)`}
        </button>

        {lastResult && (
          isReady
            ? <span className="status-ready">is_ready = true — esperando callback del coordinator...</span>
            : <span className="status-pending">
                is_ready = false — {checklist.length - filledCount} controles sin cubrir
              </span>
        )}
      </div>

      {error && (
        <div className="error-panel mt">
          <p>{error}</p>
        </div>
      )}

      {isReady && (
        <div className="waiting-verdict mt">
          El coordinator ha marcado el caso como listo. El engine está ejecutando M7.
          El veredicto aparecerá automáticamente en unos segundos...
        </div>
      )}
    </div>
  )
}
