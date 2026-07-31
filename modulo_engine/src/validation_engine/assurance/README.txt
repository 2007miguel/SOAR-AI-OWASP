ASSURANCE — Puerto al plano de aseguramiento
================================================================================

El engine no ejecuta herramientas de seguridad directamente. Esta carpeta
define el PUERTO a través del cual el engine emite el checklist de controles
que deben ser atestados y recibe de vuelta la evidencia.

La separación es deliberada: el análisis determinista (M1–M5, M7) y el
aseguramiento (attestations, red teaming, tool results) son responsabilidades
distintas. El engine define la interfaz; el aseguramiento la implementa.

Flujo dentro del ciclo de vida de un caso:
  1. M5 (ControlResolver) produce ctx.controls.critical_required
  2. El orquestador llega al assurance_gate → llama emit_checklist()
  3. El adaptador construye ctx.assurance.checklist desde los controles críticos
  4. El caso queda en AWAITING_ASSURANCE
  5. Attestations llegan vía API → se almacenan en ctx.assurance.attestations
  6. Cuando is_ready() == True, la API llama orchestrator.resume()
  7. M7 lee ctx.assurance.attestations para calcular el veredicto


RELACIÓN CON LOS OTROS COMPONENTES
--------------------------------------------------------------------------------

  modules/m5_control_resolver.py  →  produce controls.critical_required (input)
  orchestrator/orchestrator.py    →  llama emit_checklist() en el gate
  api/routes.py                   →  recibe attestations y llama is_ready() / resume()
  modules/m7_verdict_engine.py    →  consume ctx.assurance.attestations (output)


EVOLUCIÓN POR ETAPAS
--------------------------------------------------------------------------------

  Etapa 0:  ManualAdapter — el operador atestigua manualmente vía la API REST
  Etapa 1+: El assurance-coordinator (otro contenedor) implementa AssurancePort
            automatizando la recolección de evidencia y ejecutando conectores.
  El puerto (port.py) NO cambia entre etapas; solo cambia el adaptador.


ARCHIVOS
================================================================================

--------------------------------------------------------------------------------
port.py
--------------------------------------------------------------------------------
Define la interfaz AssurancePort como Protocol @runtime_checkable.

  emit_checklist(ctx) → AssessmentContext
    Recibe el contexto con controls.critical_required ya poblado (post-M5) y
    construye ctx.assurance.checklist con un ChecklistItem por cada control
    crítico. Incluye: control_id, ASI-IDs que lo requieren, categoría y
    métodos de aseguramiento sugeridos.

  is_ready(ctx) → bool
    Devuelve True cuando todos los control_id críticos tienen al menos una
    entrada en ctx.assurance.attestations. La API lo llama para decidir si
    puede invocar orchestrator.resume().

Es @runtime_checkable por el mismo motivo que Module en modules/base.py: el
orquestador puede verificar en runtime que el objeto pasado cumple la interfaz.

--------------------------------------------------------------------------------
manual_adapter.py
--------------------------------------------------------------------------------
Implementación de AssurancePort para Etapa 0 (attestación 100% manual).

  ManualAdapter.emit_checklist(ctx)
    Itera ctx.controls.critical_required y crea un ChecklistItem por cada
    control con: control_id, why = required_by_asi[], category. Los sugested_assur
    se dejan vacíos en Etapa 0 (sin KB access en el adaptador). El status inicial
    de cada ítem es NOT_IMPLEMENTED.

  ManualAdapter.is_ready(ctx)
    Compara el set de control_id críticos contra las keys de
    ctx.assurance.attestations. Devuelve True si todos están cubiertos.
    No valida el contenido de las attestations (status, evidence): eso es
    responsabilidad de M7.

En Etapa 0 el operador provee attestations a través del endpoint
POST /assessments/{id}/attest → la API las guarda en ctx.assurance.attestations
directamente, sin pasar por el adaptador.

--------------------------------------------------------------------------------
__init__.py
--------------------------------------------------------------------------------
Exporta las dos piezas que el orquestador y main.py necesitan:

  AssurancePort   → para type hints e isinstance() checks
  ManualAdapter   → instanciado en main.py y pasado al Orchestrator

================================================================================