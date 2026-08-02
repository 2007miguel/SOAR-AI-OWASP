export default function VerdictPanel({ report, onReset }) {
  if (!report) return <p>Cargando veredicto...</p>

  const {
    verdict,
    verdict_rationale,
    blocking_reasons = [],
    warnings = [],
    active_risks = [],
    active_risks_detail = [],
    active_threats = [],
    active_threats_detail = [],
    critical_controls = {},
  } = report

  const { required = [], implemented = [], partial = [], missing = [] } = critical_controls

  function labelFor(id, detail, idKey) {
    const entry = detail.find(d => d[idKey] === id)
    return entry ? `${id}:${entry.name}` : id
  }

  return (
    <div>
      <div className="card">
        <div className="verdict-header">
          <span className={`verdict-${verdict}`}>{verdict}</span>
          {verdict === 'APT' && <span style={{ color: '#155724' }}>Apto para producción</span>}
          {verdict === 'APT_WITH_RESTRICTIONS' && <span style={{ color: '#664d00' }}>Apto con restricciones</span>}
          {verdict === 'NOT_APT' && <span style={{ color: '#721c24' }}>No apto para producción</span>}
        </div>

        <p className="verdict-rationale">{verdict_rationale}</p>

        {blocking_reasons.length > 0 && (
          <>
            <p className="verdict-section-title">Razones bloqueantes</p>
            <ul className="blocking-list">
              {blocking_reasons.map((r, i) => <li key={i}>{r}</li>)}
            </ul>
          </>
        )}

        {warnings.length > 0 && (
          <>
            <p className="verdict-section-title">Advertencias</p>
            <ul className="warn-list">
              {warnings.map((w, i) => <li key={i}>{w}</li>)}
            </ul>
          </>
        )}
      </div>

      <div className="card">
        <h2>Controles Críticos</h2>

        <div className="stats-row mb">
          <span>Requeridos: <strong>{required.length}</strong></span>
          <span style={{ color: '#155724' }}>Implementados: <strong>{implemented.length}</strong></span>
          <span style={{ color: '#664d00' }}>Parciales: <strong>{partial.length}</strong></span>
          <span style={{ color: '#721c24' }}>Faltantes: <strong>{missing.length}</strong></span>
        </div>

        {missing.length > 0 && (
          <>
            <p className="verdict-section-title">Controles faltantes</p>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.3rem' }}>
              {missing.map(c => (
                <span key={c} className="badge" style={{ background: '#fce8e8', borderColor: '#c00' }}>
                  {c}
                </span>
              ))}
            </div>
          </>
        )}

        {partial.length > 0 && (
          <>
            <p className="verdict-section-title">Controles parciales</p>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.3rem' }}>
              {partial.map(c => (
                <span key={c} className="badge" style={{ background: '#fff3cd', borderColor: '#e0a800' }}>
                  {c}
                </span>
              ))}
            </div>
          </>
        )}

        {missing.length === 0 && partial.length === 0 && (
          <p style={{ color: '#155724', fontSize: '0.85rem' }}>
            Todos los controles criticos están implementados.
          </p>
        )}
      </div>

      {active_risks.length > 0 && (
        <div className="card">
          <h2>Riesgos Activos (ASIs)</h2>
          <ul className="warn-list">
            {active_risks.map(r => (
              <li key={r} style={{ marginBottom: '0.3rem' }}>
                <code style={{ fontSize: '0.78rem' }}>{labelFor(r, active_risks_detail, 'risk_id')}</code>
              </li>
            ))}
          </ul>
        </div>
      )}

      {active_threats.length > 0 && (
        <div className="card">
          <h2>Amenazas Activas</h2>
          <ul className="warn-list">
            {active_threats.map(t => (
              <li key={t} style={{ marginBottom: '0.3rem' }}>
                <code style={{ fontSize: '0.78rem' }}>{labelFor(t, active_threats_detail, 'threat_id')}</code>
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="flex-row mt">
        <button className="btn-primary" onClick={onReset}>
          Nueva Evaluación
        </button>
        {report.assessment_id && (
          <span className="hint">ID: <code>{report.assessment_id}</code></span>
        )}
      </div>
    </div>
  )
}
