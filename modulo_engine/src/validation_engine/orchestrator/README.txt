ORCHESTRATOR — Coordinación del pipeline
================================================================================

El orquestador es coordinación pura: no analiza, no valida, no calcula nada.
Lee el playbook (dato externo en YAML), instancia los módulos en orden, les
pasa el AssessmentContext enriquecido secuencialmente y registra transiciones.

Principio D5 del diseño: el playbook es dato. La secuencia de pasos no está
hardcodeada en el orquestador; vive en playbooks/full_validation.yaml y puede
cambiarse sin tocar código Python.


FLUJO DE EJECUCIÓN
--------------------------------------------------------------------------------

Un caso de evaluación tiene dos fases separadas por el assurance_gate:

  FASE 1 — run(ctx):
    M1 → M2 → M3 → M4 → M5 → [assurance_gate]
    Al llegar al gate: emite checklist, setea AWAITING_ASSURANCE, retorna.

  PAUSA (gestionada por la API + persistence):
    El caso queda guardado. Las attestations llegan vía POST /assessments/{id}/attest.
    Cuando assurance_port.is_ready(ctx) == True → la API llama resume().

  FASE 2 — resume(ctx):
    [past gate] → M7 → Reporter
    Setea COMPLETED al finalizar.

  ABORT en cualquier fase:
    Si M1 setea status = ERROR, el orquestador detiene el pipeline y retorna
    el contexto con ese status. Los módulos M2–M7 no se ejecutan.


TRANSICIONES
--------------------------------------------------------------------------------

Cada módulo ejecutado registra una Transition en ctx.transitions:
  { module: str, timestamp: datetime, status: Status }

Esto permite auditar el historial de ejecución del caso y saber exactamente
en qué paso está si se interrumpe inesperadamente.


RELACIÓN CON LOS OTROS COMPONENTES
--------------------------------------------------------------------------------

  contracts/context.py     → AssessmentContext que fluye entre módulos
  modules/                 → los módulos instanciados en el registry
  assurance/port.py        → AssurancePort que el orquestador llama en el gate
  persistence/store.py     → la API persiste ctx después de run() y resume()
  api/routes.py            → llama run() al crear un caso, resume() al completar


ARCHIVOS
================================================================================

--------------------------------------------------------------------------------
playbook.py
--------------------------------------------------------------------------------
Carga y valida el YAML de playbook.

  PlaybookStep (pydantic):
    Exactamente uno de: module (str) | assurance_gate (str).
    La validación lanza ValueError si un step tiene ambos o ninguno.
    Propiedad is_gate → True cuando el step es un assurance_gate.

  Playbook (pydantic):
    id, version, description, steps: list[PlaybookStep]

  load_playbook(path) → Playbook:
    Abre el YAML con pyyaml y valida el resultado con Playbook.model_validate().
    Lanza ValidationError si el YAML no cumple el esquema.

--------------------------------------------------------------------------------
orchestrator.py
--------------------------------------------------------------------------------
Implementa la clase Orchestrator.

  __init__(playbook, kb, assurance_port):
    Recibe el Playbook cargado, el KBService y el AssurancePort.
    Construye _registry: dict[str, Module] con una instancia de cada módulo.
    Los módulos son stateless — una sola instancia sirve para todos los casos.

  El orquestador es dueño de las transiciones de status (read/write matrix,
  assessment_context.txt §3): setea AWAITING_ASSURANCE, SCORING y COMPLETED.
  M1 setea ANALYZING/ERROR; los demás módulos no tocan status.

  run(ctx) → AssessmentContext:
    Itera steps del playbook. Si el step es gate: emite checklist, setea
    AWAITING_ASSURANCE y retorna. Si es módulo: llama _execute_module(). Si un
    módulo aborta (status == ERROR), ejecuta reporter (Reporter(error)) y retorna.

  resume(ctx) → AssessmentContext:
    Requiere ctx.status == AWAITING_ASSURANCE; lanza ValueError si no.
    Setea SCORING (M6 completó, M7 calcula), ejecuta los steps post-gate
    (M7 + Reporter) y al cerrar setea COMPLETED.

  _execute_module(name, ctx) → AssessmentContext:
    Busca el módulo en el registry (KeyError si no existe), lo ejecuta,
    registra la Transition resultante y actualiza ctx.updated_at.

--------------------------------------------------------------------------------
playbooks/full_validation.yaml
--------------------------------------------------------------------------------
El único playbook de Etapa 0. Define la secuencia completa:

  m1_intake_validation  →  valida inputs
  m2_threat_mapper      →  flags → T-IDs
  m3_risk_mapper        →  T-IDs → ASI-IDs
  m4_context_escalator  →  escalación por dominio y arquitectura
  m5_control_resolver   →  ASI-IDs → controles críticos + recomendados
  [assurance_gate]      →  pausa; espera attestations del operador
  m7_verdict_engine     →  calcula APT / APT_WITH_RESTRICTIONS / NOT_APT
  reporter              →  marca COMPLETED

El id del playbook (full_validation) se escribe en ctx.playbook_id al inicio
de run() para trazabilidad en el reporte final.

--------------------------------------------------------------------------------
__init__.py
--------------------------------------------------------------------------------
Exporta las tres piezas que main.py necesita para inicializar el sistema:

  Orchestrator    → clase principal; instanciada con playbook + kb + assurance
  Playbook        → tipo para type hints
  load_playbook   → función para cargar el YAML desde la ruta configurada

================================================================================