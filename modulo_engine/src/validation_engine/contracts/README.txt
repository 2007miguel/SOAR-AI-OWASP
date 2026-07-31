CONTRACTS — Assessment Context como código
================================================================================

Esta carpeta define el único estado compartido entre módulos del pipeline.
Cada módulo recibe el AssessmentContext, lee sus campos, escribe los suyos
y lo devuelve enriquecido. No hay canales laterales entre módulos.

Ningún archivo aquí contiene lógica de negocio: solo tipos, validación de
forma y defaults. La lógica vive en los módulos.

--------------------------------------------------------------------------------
enums.py
--------------------------------------------------------------------------------
Todos los valores cerrados del sistema en un solo lugar.

  Status           — estados del ciclo de vida de un caso (intake → completed)
  VerdictResult    — APT / APT_WITH_RESTRICTIONS / NOT_APT
  AttestationStatus — estado de cada control en la attestación (implemented…)
  BusinessDomain   — los 9 dominios de negocio válidos (Finance, Healthcare…)
  ArchitectureId   — los 3 patrones de arquitectura (ARCH-SINGLE/CENTRAL/SWARM)
  LifecyclePhase   — las 3 fases del ciclo de vida (design, build, runtime)

--------------------------------------------------------------------------------
inputs.py
--------------------------------------------------------------------------------
La capa de entrada: lo que el evaluador declara antes de que corra el pipeline.

  CapabilityFlags  — los 46 flags del wizard, cada uno como campo bool = False.
                     Agrupados por STEP (autonomy, memory, tools, auth, human,
                     multi-agent). Método .active() devuelve solo los True.
  BusinessContext  — dominio de negocio, arquitectura y fases. Usa los enums
                     cerrados: valores inválidos fallan en validación, no en
                     ejecución silenciosa.
  Aibom            — documento CycloneDX como dict flexible. Informativo en v1;
                     no deriva ASI ni controles críticos.
  InputsLayer      — agrupa los tres anteriores. Es la capa que M1 lee y valida.

--------------------------------------------------------------------------------
analysis.py
--------------------------------------------------------------------------------
La capa que construyen M1–M4. Arranca vacía y se llena módulo a módulo.

  ValidationResult — resultado de M1: ok/error + lista de errores bloqueantes.
  ArchitectureRecos — recomendaciones de M4 por arquitectura (no afectan veredicto).
  AnalysisLayer    — contiene todos los campos de análisis:
                       · active_steps, active_threats, threat_source_map (M2)
                       · active_asi, asi_trace (M3)
                       · high_risk_domain, hotl_required, escalations (M4)
                     Todos los campos tienen default vacío para que el
                     orquestador pueda instanciarla sin argumentos.

--------------------------------------------------------------------------------
controls.py
--------------------------------------------------------------------------------
La capa que escribe M5. Dos listas con propósitos distintos.

  CriticalControl  — un control obligatorio para el veredicto. Incluye qué
                     ASI-IDs lo exigen (required_by_asi).
  RecommendedControl — un control sugerido filtrado por lifecycle_phases.
  ControlsLayer    — contiene critical_required (sub-path A, decide APT/NOT_APT)
                     y recommended (sub-path B, catálogo completo filtrado).

--------------------------------------------------------------------------------
assurance.py
--------------------------------------------------------------------------------
La capa que escribe M6. Representa el estado de la attestación de controles.

  ChecklistItem    — un ítem del checklist: qué control, por qué se requiere,
                     métodos sugeridos y estado actual de la evidencia.
  Attestation      — la respuesta del evaluador a un control: status + evidencia
                     + método de aseguramiento usado.
  ToolResult       — resultado de un conector externo (herramienta de seguridad).
  AssuranceLayer   — agrupa checklist, attestations, tool_results y los flags
                     red_teaming_done e incident_response_plan que M7 consulta.

--------------------------------------------------------------------------------
verdict.py
--------------------------------------------------------------------------------
La capa final. Solo la escribe M7, y solo después de que assurance esté poblado.

  VerdictTrace     — trazabilidad completa para auditoría:
                       flags → amenazas → riesgos → controles
  VerdictLayer     — el veredicto: result (enum), label, rationale, razones
                     bloqueantes si es NOT_APT, y el trace completo.

--------------------------------------------------------------------------------
context.py
--------------------------------------------------------------------------------
El objeto raíz que fluye por todo el pipeline.

  Transition       — registro de cada cambio de estado: módulo, timestamp, status.
  AssessmentContext — contiene las 6 capas (meta + inputs + analysis + controls +
                     assurance + verdict). Las capas que empiezan vacías usan
                     default_factory. verdict arranca en None hasta que M7 lo
                     escribe. assessment_id se genera automáticamente (UUID).

--------------------------------------------------------------------------------
__init__.py
--------------------------------------------------------------------------------
Re-exporta todos los tipos públicos. Los módulos importan desde aquí:

  from validation_engine.contracts import AssessmentContext, CapabilityFlags, ...

================================================================================
