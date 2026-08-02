export default function GlobalFlags({ values, onChange }) {
  const {
    incident_response_plan,
    red_teaming_done,
    red_teaming_critical_findings,
    supply_chain_unverified,
    production_access,
    assurance_methods_used,
  } = values

  function toggle(field) {
    onChange({ ...values, [field]: !values[field] })
  }

  function handleMethods(e) {
    const raw = e.target.value
    const list = raw
      .split(',')
      .map(s => s.trim())
      .filter(Boolean)
    onChange({ ...values, assurance_methods_used: list, _methods_raw: raw })
  }

  return (
    <div>
      <h3>Proceso de Aseguramiento</h3>
      <div className="global-flags">
        <label>
          <input
            type="checkbox"
            checked={incident_response_plan}
            onChange={() => toggle('incident_response_plan')}
          />
          Plan de respuesta a incidentes implementado
        </label>
        <label>
          <input
            type="checkbox"
            checked={red_teaming_done}
            onChange={() => toggle('red_teaming_done')}
          />
          Red teaming completado
        </label>
      </div>

      <div className="form-row mt" style={{ alignItems: 'flex-start' }}>
        <label style={{ minWidth: '200px', paddingTop: '3px' }}>
          Métodos de aseguramiento usados:
        </label>
        <input
          type="text"
          placeholder="ASSUR-01, ASSUR-02, ..."
          value={values._methods_raw || assurance_methods_used.join(', ')}
          onChange={handleMethods}
          style={{ minWidth: '260px' }}
        />
      </div>

      <hr className="section-divider" />

      <h3>Señales de Riesgo (M7)</h3>
      <p className="signal-warning">
        Activar estas señales puede resultar en veredicto NOT_APT aunque todos los controles estén implementados.
      </p>
      <div className="global-flags">
        <label>
          <input
            type="checkbox"
            checked={red_teaming_critical_findings}
            onChange={() => toggle('red_teaming_critical_findings')}
          />
          Red teaming encontró vulnerabilidades críticas sin mitigar
        </label>
        <label>
          <input
            type="checkbox"
            checked={supply_chain_unverified}
            onChange={() => toggle('supply_chain_unverified')}
          />
          Hay componentes del supply chain sin verificar
        </label>
        <label>
          <input
            type="checkbox"
            checked={production_access}
            onChange={() => toggle('production_access')}
          />
          El agente tiene acceso directo a producción
        </label>
      </div>
    </div>
  )
}
