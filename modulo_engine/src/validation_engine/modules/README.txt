MODULES — Módulos del pipeline de validación
================================================================================

Cada archivo es un paso del pipeline. Los módulos son deterministas y sin estado
propio: reciben el AssessmentContext, leen sus campos declarados, escriben los
suyos y lo devuelven enriquecido. Nunca se comunican entre sí directamente.

El orquestador los ejecuta en el orden definido en el playbook YAML. Cada módulo
declara explícitamente qué campos lee (reads) y qué campos escribe (writes),
lo que hace el contrato auditable en runtime.

El único acceso externo permitido es al KBService (solo lectura). Ningún módulo
hardcodea flags, T-IDs, ASI-IDs ni CTRL-IDs: todo lo consulta al KB.

--------------------------------------------------------------------------------
base.py
--------------------------------------------------------------------------------
Define el Protocol Module que todos los módulos implementan.

  name   : identificador del módulo (string)
  reads  : campos del AssessmentContext que el módulo lee (documentación del contrato)
  writes : campos que el módulo escribe (documentación del contrato)
  run(ctx, kb) → AssessmentContext

Es @runtime_checkable, lo que permite al orquestador verificar en tiempo de
ejecución que un objeto cumple la interfaz antes de invocarlo.

--------------------------------------------------------------------------------
m1_intake_validation.py — M1 Intake & Validation
--------------------------------------------------------------------------------
Primer módulo del pipeline. Valida los inputs antes de gastar análisis.

Escribe: analysis.validation, analysis.warnings, status

Validaciones que ejecuta:
  - lifecycle_phases no puede ser lista vacía → ERROR bloqueante
    (el campo es required pero podría llegar como [])
  - Si architecture_id es ARCH-CENTRAL o ARCH-SWARM y multi_agent_architecture
    es false → WARNING de inconsistencia
  - Si multi_agent_architecture es true pero architecture_id es ARCH-SINGLE
    → WARNING de inconsistencia en dirección inversa
  - Si aibom está ausente → WARNING con aviso de impacto en CTRL-SC-01

Si hay errores bloqueantes: status = ERROR y el orquestador aborta el pipeline.
Si solo hay warnings: status = ANALYZING y el pipeline continúa.

--------------------------------------------------------------------------------
m2_threat_mapper.py — M2 ThreatMapper (capability_flags → T-IDs)
--------------------------------------------------------------------------------
Traduce los flags activos del wizard a amenazas concretas del catálogo OWASP.

Escribe: analysis.active_steps, analysis.active_threats,
         analysis.threat_source_map, analysis.critical_systems_path

Lógica:
  - Para cada flag=True: busca STEPs en capability_taxonomy que lo contengan
    y acumula sus activated_threats en un set (sin duplicados).
  - Path especial critical_systems_access: no está en ningún STEP, se procesa
    directamente contra OC-KC6.6 en operational_capabilities.
  - Construye threat_source_map con entradas del tipo "STEP-1[flag_name]"
    o "OC-KC6.6[flag_name]" para trazabilidad completa en M7.

No usa activated_risks de los STEPs (es un caché, no una fuente).
No deriva amenazas de architecture_types (solo recomendaciones).

--------------------------------------------------------------------------------
m3_risk_mapper.py — M3 RiskMapper (T-IDs → ASI-IDs, vía Appendix A)
--------------------------------------------------------------------------------
Eleva las amenazas activas a los riesgos del OWASP Top 10 for Agentic AI.

Escribe: analysis.active_asi, analysis.asi_trace

Lógica:
  - Para cada T-ID activo: consulta kb.maps_to_asi() que replica la matriz
    oficial Appendix A del documento Threats and Mitigations.
  - Acumula ASI-IDs en un set (sin duplicados).
  - Construye asi_trace: ASI-ID → [T-IDs que lo activaron].
  - T9 (Identity Spoofing): maps_to_asi = [] por diseño OWASP. T9 permanece
    como amenaza activa con controles recomendados, pero no aporta ningún ASI.

La relación T-ID → ASI es M:N: un T-ID puede activar varios ASIs y un ASI
puede ser activado por varios T-IDs.

--------------------------------------------------------------------------------
m4_context_escalator.py — M4 ContextEscalator
--------------------------------------------------------------------------------
Aplica el contexto operativo del negocio sobre el análisis de amenazas.

Escribe: analysis.high_risk_domain, analysis.hotl_required,
         analysis.architecture_recos, analysis.escalations

Lógica:
  - Si business_domain está en kb.high_risk_domains() (dominios EU AI Act):
    → high_risk_domain = True
    → hotl_required = True (Human-Over-The-Loop, supervisión continua)
    → registra la escalación en escalations[]
  - Obtiene recomendaciones de arquitectura para el arch_id declarado más el
    baseline transversal ARCH-CROSS (siempre incluido).
  - Las recomendaciones de arquitectura van SOLO a architecture_recos: no
    añaden amenazas ni ASI al conjunto que decide el veredicto.

--------------------------------------------------------------------------------
m5_control_resolver.py — M5 ControlResolver
--------------------------------------------------------------------------------
Determina qué controles son obligatorios para el veredicto y cuáles recomendados.
Opera en dos sub-paths paralelos con propósitos distintos.

Escribe: controls.critical_required, controls.recommended

Sub-path A — controles críticos (veredicto):
  - Por cada ASI activo → kb.critical_controls_for_asi() → CTRL-IDs obligatorios.
  - Si high_risk_domain: añade CTRL-DEP-05 con required_by=["high_risk_domain"].
  - Enriquece cada control con nombre, descripción y categoría del KB.
  - Un control puede ser requerido por múltiples ASIs (relación M:N).

Sub-path B — controles recomendados (reporte):
  - Por cada T-ID activo → kb.controls_mitigating() → lista de controles.
  - Filtra por lifecycle_phases del business_context.
  - Deduplica (un control puede mitigar múltiples T-IDs activos).
  - El campo mitigates solo incluye los T-IDs activos en esta evaluación.

La función _category() mapea el prefijo del control_id (CTRL-AUTH, CTRL-MON,
etc.) a un nombre de dominio legible.

--------------------------------------------------------------------------------
m7_verdict_engine.py — M7 VerdictEngine
--------------------------------------------------------------------------------
Calcula el veredicto final. Es el único módulo con criterio propio del sistema
(OWASP no define aptitud para producción; este es el aporte declarado).

Escribe: verdict   (el status lo gestiona el orquestador — ver read/write matrix)

Orden de evaluación (NOT_APT tiene prioridad):

  NOT_APT si cualquiera de:
    - Control crítico de ASI en high_severity_risks (ASI01/02/03/05/06)
      tiene status = not_implemented
    - incident_response_plan = false
    - CTRL-MON-01 (logging inmutable) = not_implemented
    - supply_chain_unverified = true Y production_access = true
    - red_teaming_done = true Y red_teaming_critical_findings = true

  APT si todos:
    - Todos los controles críticos = implemented
    - Red teaming completado para los ASIs de alta severidad activos
    - Human-Over-The-Loop ok (CTRL-DEP-05 implemented si high_risk_domain)

  APT_WITH_RESTRICTIONS: caso intermedio (no hay NOT_APT pero tampoco APT pleno)

La función _build_trace() construye el objeto VerdictTrace para auditoría
invirtiendo las estructuras del contexto:
  threat_source_map  → flags_to_threats  (flag → [T-IDs])
  asi_trace          → threats_to_risks  (T-ID → [ASI-IDs])
  critical_required  → risks_to_controls (ASI-ID → [CTRL-IDs])

--------------------------------------------------------------------------------
reporter.py — R Reporter
--------------------------------------------------------------------------------
Último paso del pipeline. No analiza: ensambla.

  Reporter.run(ctx, kb) → AssessmentContext
    Produce el reporte externo; NO muta el contexto (no escribe status).
    El orquestador lo llama como módulo final del playbook y es él quien marca
    ctx.status = COMPLETED al cerrar (read/write matrix: Reporter no escribe status).

  build_report(ctx) → dict
    Función independiente que el orquestador (o la API) llama después de run()
    para obtener el documento de reporte completo. Incluye:
      - Veredicto con label, rationale y blocking_reasons
      - Active flags, threats, risks
      - high_risk_domain, hotl_required, critical_systems_path
      - Critical controls: required / implemented / partial / missing
      - Recommended controls filtrados
      - Assurance methods used, warnings
      - Trace completo para auditoría

--------------------------------------------------------------------------------
__init__.py
--------------------------------------------------------------------------------
Exporta todos los módulos y la función build_report para que el orquestador
importe desde un único punto:

  from validation_engine.modules import M1IntakeValidation, M2ThreatMapper, ...

================================================================================
