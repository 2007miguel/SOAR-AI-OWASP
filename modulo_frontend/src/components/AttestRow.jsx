export default function AttestRow({ item, value, onChange }) {
  const {
    control_id, control_name = '', control_description = '',
    why, why_detail = [],
    threats, threats_detail = [],
    category, suggested_assur, suggested_assur_detail = [],
  } = item
  const { status, evidence } = value

  function nameFor(id, detail, idKey) {
    const entry = detail.find(d => d[idKey] === id)
    return entry ? entry.name : null
  }

  return (
    <tr>
      <td>
        <code style={{ fontSize: '0.75rem' }}>{control_id}</code>
        {control_name && (
          <div style={{ fontSize: '0.72rem', fontWeight: 600, marginTop: '0.15rem' }}>
            {control_name}
          </div>
        )}
        {control_description && (
          <div style={{ fontSize: '0.68rem', color: '#555', marginTop: '0.1rem', maxWidth: '220px' }}>
            {control_description}
          </div>
        )}
      </td>
      <td>
        {why.map(a => {
          const name = nameFor(a, why_detail, 'asi_id')
          const detail = why_detail.find(d => d.asi_id === a)
          const llm = detail?.llm_top10_mapping?.join(', ')
          const tooltip = [detail?.scope, llm].filter(Boolean).join(' | ')
          return (
            <span key={a} className="badge" title={tooltip || undefined}>
              {a}{name ? `:${name}` : ''}
            </span>
          )
        })}
      </td>
      <td>
        {threats.length > 0
          ? threats.map(t => {
              const name = nameFor(t, threats_detail, 'threat_id')
              const detail = threats_detail.find(d => d.threat_id === t)
              return (
                <span
                  key={t}
                  className="badge"
                  style={{ background: '#fef3c7', borderColor: '#d97706' }}
                  title={detail?.description || undefined}
                >
                  {t}{name ? `:${name}` : ''}
                </span>
              )
            })
          : <span style={{ color: '#aaa' }}>—</span>}
      </td>
      <td>
        <span className="badge">{category}</span>
      </td>
      <td>
        {suggested_assur.length > 0
          ? suggested_assur.map(s => {
              const detail = suggested_assur_detail.find(d => d.method_id === s)
              const tooltip = detail?.description || undefined
              return (
                <span key={s} className="badge" title={tooltip}>
                  {s}{detail?.name ? `:${detail.name}` : ''}
                </span>
              )
            })
          : <span style={{ color: '#aaa' }}>—</span>}
      </td>
      <td>
        <select
          value={status}
          onChange={e => onChange({ status: e.target.value, evidence })}
        >
          <option value="">— sin atestar —</option>
          <option value="implemented">implemented</option>
          <option value="partial">partial</option>
          <option value="not_implemented">not_implemented</option>
        </select>
      </td>
      <td>
        <input
          type="text"
          placeholder="evidencia (opcional)"
          value={evidence}
          disabled={!status}
          onChange={e => onChange({ status, evidence: e.target.value })}
          style={{ minWidth: '140px' }}
        />
      </td>
    </tr>
  )
}
