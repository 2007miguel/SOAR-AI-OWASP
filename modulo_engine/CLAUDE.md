# Engine — Motor Determinista de Validación OWASP

## Qué es este módulo

Sistema de cumplimiento prescriptivo OWASP para agentes de IA. Dado un agente con capacidades declaradas, determina qué controles de seguridad OWASP son obligatorios y produce un veredicto: **APT / APT_WITH_RESTRICTIONS / NOT_APT**.

No es un escáner dinámico ni analiza código fuente. Evalúa capacidades declaradas contra la taxonomía OWASP y verifica si los controles están implementados.

**Stack:** Python · FastAPI (gateway) · pydantic (contratos y validación) · pydantic-settings (config)

**KB:** montado como volumen read-only (`kb_volume/`). Nunca se hornea en la imagen. Cambiar OWASP = nuevo JSON, sin tocar código.

---

## Estructura de archivos

```
engine/
├── pyproject.toml
├── Dockerfile
├── docker-compose.yml          # Etapa 0: engine + assessment-db
├── .env.example                # KB_PATH, DB_URL, LOG_LEVEL
│
├── kb_volume/                  # VOLUMEN RO (no incluir en imagen)
│   └── owasp_asi_knowledge_base.json
│
└── src/validation_engine/
    ├── main.py                 # arranque FastAPI + carga KB + selfcheck
    ├── config.py               # settings via pydantic-settings
    ├── logging.py              # logging estructurado (trace_id por caso)
    │
    ├── contracts/              # Assessment Context como código pydantic
    │   ├── context.py          # AssessmentContext (raíz)
    │   ├── inputs.py           # CapabilityFlags, BusinessContext, Aibom
    │   ├── analysis.py         # steps, threats, asi, escalations
    │   ├── controls.py         # critical_required, recommended
    │   ├── assurance.py        # checklist, attestations, tool_results
    │   ├── verdict.py          # result, rationale, trace
    │   └── enums.py            # Status, VerdictResult, categorías
    │
    ├── kb/
    │   ├── models.py           # modelos pydantic del KB JSON
    │   ├── loader.py           # carga y valida el JSON; fija kb_version
    │   ├── service.py          # API de consulta (ver sección KB Service)
    │   └── selfcheck.py        # cobertura flags + activated_risks == Appendix A
    │
    ├── orchestrator/
    │   ├── orchestrator.py     # ejecuta el playbook sobre el contexto
    │   ├── playbook.py         # carga/valida el playbook YAML
    │   └── playbooks/
    │       └── full_validation.yaml
    │
    ├── modules/
    │   ├── base.py             # Protocol Module (reads/writes/run)
    │   ├── m1_intake_validation.py
    │   ├── m2_threat_mapper.py
    │   ├── m3_risk_mapper.py
    │   ├── m4_context_escalator.py
    │   ├── m5_control_resolver.py
    │   ├── m7_verdict_engine.py
    │   └── reporter.py
    │
    ├── assurance/
    │   ├── port.py             # interfaz AssurancePort
    │   └── manual_adapter.py   # Etapa 0: attestación 100% manual
    │
    ├── persistence/
    │   ├── store.py            # interfaz AssessmentStore
    │   └── sqlalchemy_store.py # SQLite (Etapa 0) → Postgres (luego)
    │
    └── api/
        ├── routes.py           # POST /assessments, GET /assessments/{id}
        └── dto.py              # DTOs request/response
```

---

## El Assessment Context (objeto de caso)

Es el único estado compartido entre módulos. El orquestador lo crea; cada módulo lo recibe, lee ciertos campos, escribe los suyos y lo devuelve enriquecido. **No hay canales laterales entre módulos.**

### Ciclo de vida (campo `status`)

```
intake → analyzing → awaiting_assurance → scoring → completed
intake → error          (si M1 falla)
awaiting_assurance → awaiting_assurance   (evidencia parcial)
completed → analyzing   (playbook REASSESS)
```

### Capas y propietarios

| Capa | Escribe | Contenido clave |
|------|---------|-----------------|
| meta | Orquestador | assessment_id, kb_version, status, transitions |
| inputs | M1 | capability_flags (46), business_context, aibom |
| analysis | M1–M4 | active_steps, active_threats, active_asi, escalations |
| controls | M5 | critical_required, recommended |
| assurance | M6 | checklist, attestations, tool_results |
| verdict | M7 | result, rationale, blocking_reasons, trace |

### Matriz completa lee/escribe por módulo

| Módulo | Lee | Escribe |
|--------|-----|---------|
| Orquestador | todo | meta.*, status, transitions |
| M1 Intake | inputs.* | analysis.validation, analysis.warnings, status |
| M2 ThreatMapper | inputs.capability_flags, KB: capability_taxonomy, operational_capabilities | analysis.active_steps, active_threats, threat_source_map, critical_systems_path |
| M3 RiskMapper | analysis.active_threats, KB: threat_catalog.maps_to_asi | analysis.active_asi, analysis.asi_trace |
| M4 ContextEscalator | inputs.business_context, analysis.active_asi, KB: high_risk_business_domains, architecture_types | analysis.high_risk_domain, hotl_required, architecture_recos, escalations |
| M5 ControlResolver | analysis.active_asi, active_threats, inputs.business_context.lifecycle_phases, analysis.high_risk_domain, KB: critical_controls_by_risk, controls_catalog | controls.critical_required, controls.recommended |
| M6 Assurance | controls.critical_required, KB: controls metadata, assurance_methods | assurance.* |
| M7 VerdictEngine | controls.critical_required, assurance.*, analysis.high_risk_domain, KB: verdict_framework, high_severity_risks | verdict.* |
| R Reporter | todo | (reporte externo) |

---

## Lógica del pipeline (qué implementa cada módulo)

### M1 — Validación de inputs
- Verificar presencia de `business_domain`, `architecture_id`, `lifecycle_phases` → ERROR bloqueante si falta alguno.
- Cruzar: si `architecture_id` es ARCH-CENTRAL o ARCH-SWARM, `multi_agent_architecture` debe ser `true` → WARNING si no coincide.

> Nota de responsabilidad: la **cobertura de flags (wizard vs KB)** es un invariante estático KB↔wizard, no una propiedad por-request. Se valida **al arranque** en `kb/selfcheck.py` (bloqueante), no en M1 (arquitectura_sistema.txt §8; estructura_engine.txt §2/§3). Los `capability_flags` llegan ya resueltos en el request.
- El aibom en v1 es informativo: evidencia candidata para CTRL-SC-01, señal para data-protection, insumo para supply chain NOT_APT. No deriva ASI ni controles críticos.

### M2 — Flags → T-IDs (ThreatMapper)
- Para cada flag `= true`: buscar en `capability_taxonomy.steps[].capability_flags` → extraer `activated_threats[]` → acumular en Set.
- **Path especial `critical_systems_access`:** ir directo a `operational_capabilities.OC-KC6.6` (no está en ningún STEP). Extraer `core_threats[]` y marcar HOTL.
- **La arquitectura NO añade T-IDs al veredicto.** `architecture_types` solo aporta recomendaciones (security_practices, priority_control_domains).
- Producir `threat_source_map`: T-ID → [STEPs que lo activaron].

### M3 — T-IDs → ASI-IDs (RiskMapper)
- Para cada T-ID activo: leer `threat_catalog[T-ID].maps_to_asi[]` (réplica exacta de Appendix A OWASP) → acumular en Set.
- **`capability_taxonomy.activated_risks` es un caché derivado, NO fuente.** Nunca usarlo como atajo.
- **T9 especial:** `maps_to_asi = []`. T9 se activa como amenaza y recibe controles vía `controls_catalog`, pero no aporta ASI ni controles críticos al veredicto.
- `cross_mapping` (Appendix A indexada por ASI) sirve solo para verificación cruzada.

### M4 — Escalación por contexto (ContextEscalator)
- Si `business_domain` está en `verdict_framework.high_risk_business_domains.domains[]`: añadir CTRL-DEP-05 a críticos, marcar `high_risk_domain = true` y `hotl_required = true`.
- La arquitectura solo genera recomendaciones. Incluir siempre ARCH-CROSS como baseline.
- Las amenazas multi-agente (T12, T13, T14) entran al veredicto por capability_flags (STEP-6), no por el architecture_id.

### M5 — Resolución de controles (ControlResolver)

**Sub-path A (veredicto):** para cada ASI activo → `verdict_framework.critical_controls_by_risk[ASI-ID]` → set de CTRL-IDs. Si `high_risk_domain = true`, añadir CTRL-DEP-05. Enriquecer con metadata de `controls_catalog`.

Mapa crítico en KB:
```
ASI01 → CTRL-PROMPT-01, CTRL-PROMPT-02, CTRL-TOOL-04, CTRL-MON-01
ASI02 → CTRL-TOOL-01, CTRL-TOOL-02, CTRL-TOOL-03, CTRL-MON-03
ASI03 → CTRL-AUTH-01, CTRL-AUTH-02, CTRL-AUTH-03, CTRL-DEP-04
ASI04 → CTRL-SC-01, CTRL-SC-02, CTRL-SC-03
ASI05 → CTRL-TOOL-02, CTRL-TOOL-06, CTRL-DEP-01
ASI06 → CTRL-DATA-04, CTRL-DATA-05, CTRL-PROMPT-01, CTRL-MON-01
ASI07 → CTRL-INTERAGENT-01, CTRL-INTERAGENT-03, CTRL-INTERAGENT-04
ASI08 → CTRL-MON-02, CTRL-MON-04, CTRL-DEP-06
ASI09 → CTRL-TOOL-04, CTRL-MON-01, CTRL-DEP-05
ASI10 → CTRL-INTERAGENT-06, CTRL-MON-04, CTRL-DEP-06
```

**Sub-path B (recomendaciones):** para cada T-ID activo → `controls_catalog[].controls[].mitigates_threats[]` → filtrar por `lifecycle_phases` del `business_context` → deduplicar.

### M6 — Assurance (puerto, no ejecuta tools)
- Emite checklist de attestación (control_id, nombre, descripción, por qué se requiere).
- Sugiere ASSUR-IDs según `assurance_methods[].covers_risks[]` para los ASI activos.
- Si algún ASI activo está en `high_severity_risks` (ASI01/02/03/05/06) y `red_teaming_completed = false` → veredicto máximo es APT_WITH_RESTRICTIONS.
- Etapa 0: `manual_adapter.py` (attestación 100% manual). Etapas siguientes: el assurance-coordinator implementa el puerto.

### M7 — Veredicto (VerdictEngine)
Evaluar en orden: NOT_APT → APT → APT_WITH_RESTRICTIONS.

**NOT_APT** si cualquiera de:
- Control crítico de ASI en `high_severity_risks` (ASI01/02/03/05/06) = `not_implemented`
- `incident_response_plan = false`
- CTRL-MON-01 = `not_implemented`
- aibom: componentes sin verificar con `production_access = true`
- Red teaming con vulnerabilidades críticas sin mitigar

**APT** si todos:
- Todos los controles críticos = `implemented`
- `red_teaming_completed = true` para ASI de `high_severity_risks`
- `incident_response_plan = true`
- CTRL-MON-01 = `implemented`
- Si `high_risk_domain`: CTRL-DEP-05 = `implemented`

**APT_WITH_RESTRICTIONS** si no cumple NOT_APT ni APT.

---

## La interfaz Module

```python
class Module(Protocol):
    name: str
    reads:  list[str]   # ej. "analysis.active_threats"
    writes: list[str]   # ej. "analysis.active_asi"
    def run(self, ctx: AssessmentContext, kb: KBService) -> AssessmentContext: ...
```

El orquestador puede verificar en runtime que un módulo solo escribió los campos de `writes`. Los campos en `reads`/`writes` usan notación dot sobre el Assessment Context.

---

## API del KB Service (kb/service.py)

Los módulos consultan el KB **solo** por estos métodos, nunca recorriendo el JSON directamente:

```python
steps_for_flag(flag: str) -> list[str]                    # → [step_id]
threats_for_step(step_id: str) -> list[str]               # → [T-ID]
maps_to_asi(threat_id: str) -> list[str]                  # → [ASI-ID] (Appendix A)
oc_for_flag(flag: str) -> OperationalCapability | None    # rama critical_systems_access
critical_controls_for_asi(asi_id: str) -> list[str]       # → [CTRL-ID]
controls_mitigating(threat_id: str) -> list[Control]
controls_for_phases(controls, phases) -> list[Control]    # filtro lifecycle
high_risk_domains() -> list[str]
high_severity_risks() -> list[str]                        # ASI01/02/03/05/06
architecture_recommendations(arch_id: str) -> dict
assurance_methods_for_asi(asi_id: str) -> list[str]       # → [ASSUR-ID]
kb_version() -> str
```

---

## Invariantes críticos

**I1. Inmutabilidad hacia atrás.** Un módulo nunca reescribe campos de una capa anterior. M3 no toca inputs; M7 no toca analysis.

**I2. Fuente única de ASI.** `active_asi` se deriva exclusivamente de `active_threats` vía `threat_catalog.maps_to_asi` (Appendix A). No desde `activated_risks` del STEP (es caché), ni desde la arquitectura, ni desde perfiles.

**I3. Arquitectura no altera el veredicto.** `architecture_recos` es informativo. Nunca modifica `active_asi` ni `active_threats`. Las amenazas multi-agente entran por capability_flags, no por `architecture_id`.

**I4. El veredicto solo existe después del aseguramiento.** `verdict.*` solo se escribe si `assurance.*` está poblado.

**I5. Reproducibilidad.** Mismos (inputs + kb_version) → mismas capas analysis y controls siempre. Solo assurance y verdict dependen de evidencia externa.

**I6. Trazabilidad obligatoria.** Todo ASI activo debe rastrearse a un T-ID y a un flag. Todo control crítico debe rastrearse a un ASI.

---

## Orden de construcción

1. `contracts/` — el modelo de datos del que todo depende
2. `kb/` — loader + service + selfcheck (falla el arranque si el KB es incoherente)
3. `modules/` M1–M5, M7 — con golden tests por módulo
4. `reporter.py` — ensamblado del reporte
5. `orchestrator/` + `full_validation.yaml` — flujo end-to-end con attestación manual
6. `persistence/` — guardar y reanudar casos (SQLite en Etapa 0)
7. `api/` + `main.py` + `Dockerfile` + `docker-compose.yml` — exponer por REST

---

## Testing

- **Golden tests** (mismos inputs → mismos ASI/controles): garantía de fidelidad al marco OWASP.
- `tests/kb/test_selfcheck.py`: verifica que `activated_risks` == derivación real de Appendix A.
- `tests/modules/test_m3_risk_mapper.py`: golden — set de flags → set de ASI esperado.
- `tests/orchestrator/test_full_validation.py`: flujo end-to-end con attestación manual.
- Fixtures en `tests/fixtures/`: inputs de ejemplo + KB de prueba reducido.
- Los módulos son deterministas y se testean de forma aislada (no necesitan el orquestador).

---

## Reglas de diseño

- **Un módulo del pipeline = un archivo** en `modules/`. Nombre refleja el paso.
- **Los contratos son código (pydantic).** No hay DTOs sueltos en los módulos; todo usa `contracts/`.
- **Toda la semántica OWASP vive en kb/.** Ningún módulo hardcodea flags, T-IDs, ASI-IDs o CTRL-IDs.
- **El playbook es dato.** `full_validation.yaml` define la secuencia; el orquestador la interpreta.
- **assurance/ es un puerto.** El engine emite el checklist y recibe evidencia; no ejecuta herramientas de seguridad.
- No existe camino directo flag → ASI. El flujo obligatorio es: `flag → STEP → T-IDs → ASI-IDs`.

---

## Referencia de archivos de diseño

| Documento | Ruta | Contenido |
|-----------|------|-----------|
| Estructura del engine | `archivos_desarrollo/arquitectura/estructura_modulos/estructura_engine.txt` | Árbol de archivos, principios, orden de construcción |
| Contrato del contexto | `archivos_desarrollo/arquitectura/assessment_context.txt` | AssessmentContext completo, matriz lee/escribe, invariantes |
| Guía del KB | `archivos_desarrollo/knoledge_base_sistema/owasp_asi_knowledge_base_GUIA.txt` | Estructura del JSON, 15 secciones, pipeline conceptual |
| Guía de implementación | `archivos_desarrollo/knoledge_base_sistema/pipeline_implementacion_GUIA.txt` | Qué implementar en código por módulo, lógica de veredicto |
| Knowledge Base | `archivos_desarrollo/knoledge_base_sistema/owasp_asi_knowledge_base.json` | Datos OWASP (leer con kb/service.py, nunca directo) |
