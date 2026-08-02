import { useState, useEffect } from 'react'
import { createAssessment, getAssessment } from './api'
import WizardForm from './components/WizardForm'
import ChecklistPanel from './components/ChecklistPanel'
import VerdictPanel from './components/VerdictPanel'
import './App.css'

export default function App() {
  const [phase, setPhase] = useState('idle')
  const [assessmentId, setAssessmentId] = useState(null)
  const [checklist, setChecklist] = useState([])
  const [report, setReport] = useState(null)
  const [errorMsg, setErrorMsg] = useState(null)

  useEffect(() => {
    if (phase !== 'awaiting_assurance') return

    const id = setInterval(async () => {
      try {
        const data = await getAssessment(assessmentId)
        if (data.status === 'completed') {
          clearInterval(id)
          setReport(data.report)
          setPhase('completed')
        } else if (data.status === 'error') {
          clearInterval(id)
          setErrorMsg('El engine reportó un error interno.')
          setPhase('error')
        }
      } catch {
        // ignore transient errors during polling
      }
    }, 2000)

    return () => clearInterval(id)
  }, [phase, assessmentId])

  async function handleCreate(payload) {
    try {
      const data = await createAssessment(payload)
      setAssessmentId(data.assessment_id)
      setChecklist(data.checklist)
      setPhase('awaiting_assurance')
    } catch (e) {
      setErrorMsg(e.detail || JSON.stringify(e))
      setPhase('error')
    }
  }

  function handleReset() {
    setPhase('idle')
    setAssessmentId(null)
    setChecklist([])
    setReport(null)
    setErrorMsg(null)
  }

  return (
    <div className="app">
      <header className="app-header">
        <h1>SOAR-AI OWASP</h1>
        <p className="subtitle">Sistema de validación prescriptiva de agentes de IA (OWASP ASI)</p>
        {assessmentId && (
          <p className="aid">
            Assessment ID: <code>{assessmentId}</code>
          </p>
        )}
      </header>

      <main>
        {phase === 'idle' && (
          <WizardForm onSubmit={handleCreate} />
        )}

        {phase === 'awaiting_assurance' && (
          <ChecklistPanel
            assessmentId={assessmentId}
            checklist={checklist}
          />
        )}

        {phase === 'completed' && (
          <VerdictPanel report={report} onReset={handleReset} />
        )}

        {phase === 'error' && (
          <div className="error-panel">
            <h2>Error</h2>
            <p>{errorMsg || 'Error desconocido'}</p>
            <button onClick={handleReset} className="btn-primary">Reiniciar</button>
          </div>
        )}
      </main>
    </div>
  )
}
