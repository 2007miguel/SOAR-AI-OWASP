import { useState } from 'react'
import { FLAG_GROUPS, ALL_FLAG_KEYS, ARCH_FLAG_SUGGESTIONS } from '../wizard_flags'

const DOMAINS = [
  'Technology', 'Finance', 'Healthcare', 'Education',
  'Critical Infrastructure', 'Legal', 'Law Enforcement', 'Retail', 'Other',
]

const ARCHITECTURES = [
  { value: 'ARCH-SINGLE',  label: 'ARCH-SINGLE — Agente único' },
  { value: 'ARCH-CENTRAL', label: 'ARCH-CENTRAL — Multi-agente centralizado' },
  { value: 'ARCH-SWARM',   label: 'ARCH-SWARM — Multi-agente enjambre' },
]

const LIFECYCLE_OPTIONS = ['design', 'build', 'runtime']

function buildInitialFlags() {
  return Object.fromEntries(ALL_FLAG_KEYS.map(k => [k, false]))
}

export default function WizardForm({ onSubmit }) {
  const [flags, setFlags] = useState(buildInitialFlags())
  const [domain, setDomain] = useState('Technology')
  const [arch, setArch] = useState('ARCH-SINGLE')
  const [phases, setPhases] = useState(['runtime'])
  const [submitting, setSubmitting] = useState(false)

  function handleArchChange(e) {
    const newArch = e.target.value
    setArch(newArch)
    const suggestions = ARCH_FLAG_SUGGESTIONS[newArch] || []
    if (suggestions.length > 0) {
      setFlags(prev => {
        const next = { ...prev }
        suggestions.forEach(k => { next[k] = true })
        return next
      })
    }
  }

  function toggleFlag(key) {
    setFlags(prev => ({ ...prev, [key]: !prev[key] }))
  }

  function togglePhase(phase) {
    setPhases(prev =>
      prev.includes(phase) ? prev.filter(p => p !== phase) : [...prev, phase]
    )
  }

  async function handleSubmit(e) {
    e.preventDefault()
    if (phases.length === 0) {
      alert('Selecciona al menos una fase del ciclo de vida.')
      return
    }
    setSubmitting(true)
    try {
      await onSubmit({
        capability_flags: flags,
        business_context: {
          business_domain: domain,
          architecture_id: arch,
          lifecycle_phases: phases,
        },
      })
    } finally {
      setSubmitting(false)
    }
  }

  const activeCount = Object.values(flags).filter(Boolean).length

  return (
    <form onSubmit={handleSubmit}>
      <div className="card">
        <h2>1. Contexto del Negocio</h2>

        <div className="form-row">
          <label>Dominio:</label>
          <select value={domain} onChange={e => setDomain(e.target.value)}>
            {DOMAINS.map(d => <option key={d} value={d}>{d}</option>)}
          </select>
        </div>

        <div className="form-row">
          <label>Arquitectura:</label>
          <select value={arch} onChange={handleArchChange}>
            {ARCHITECTURES.map(a => (
              <option key={a.value} value={a.value}>{a.label}</option>
            ))}
          </select>
        </div>

        {arch !== 'ARCH-SINGLE' && (
          <p className="hint">
            Se activaron automáticamente los flags de STEP-6 correspondientes a esta arquitectura.
          </p>
        )}

        <div className="form-row" style={{ alignItems: 'flex-start' }}>
          <label style={{ paddingTop: '2px' }}>Fases del ciclo de vida:</label>
          <div className="lifecycle-row">
            {LIFECYCLE_OPTIONS.map(ph => (
              <label key={ph}>
                <input
                  type="checkbox"
                  checked={phases.includes(ph)}
                  onChange={() => togglePhase(ph)}
                />
                {ph}
              </label>
            ))}
          </div>
        </div>
      </div>

      <div className="card">
        <h2>2. Capacidades del Agente ({activeCount} activas)</h2>
        <p className="hint mb">Marca todas las capacidades que el agente usa o podría usar.</p>

        {FLAG_GROUPS.map(group => (
          <div key={group.id} className="flag-section">
            <div className="flag-section-title">{group.label}</div>
            <div className="flags-grid">
              {group.flags.map(f => (
                <label key={f.key}>
                  <input
                    type="checkbox"
                    checked={flags[f.key]}
                    onChange={() => toggleFlag(f.key)}
                  />
                  {f.label}
                </label>
              ))}
            </div>
          </div>
        ))}
      </div>

      <div className="flex-row">
        <button type="submit" className="btn-primary" disabled={submitting}>
          {submitting ? 'Iniciando análisis...' : 'Iniciar Evaluación OWASP ASI'}
        </button>
        <span className="hint">M1–M5 se ejecutarán automáticamente</span>
      </div>
    </form>
  )
}
