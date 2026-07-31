KB — Knowledge Base Service
================================================================================

Único lugar del sistema que entiende la estructura del knowledge base OWASP.
Los módulos del pipeline nunca leen el JSON directamente: siempre consultan
a través del KBService.

El KB se carga una vez al arrancar la aplicación y vive en memoria como un
singleton de solo lectura durante toda la vida del proceso.


ESTRUCTURA DEL VOLUMEN ESPERADA
================================================================================

Este código espera recibir el KB desde un directorio montado como volumen RO.
La especificación completa del volumen está en:

  engine/kb_volume/README.txt

Lo que este código espera encontrar en ese directorio:

  ARCHIVO                              OBLIGATORIO   USADO POR
  ─────────────────────────────────────────────────────────────────────────────
  owasp_asi_knowledge_base.json        SÍ            loader.py → KBService
  agent_validation_wizard.json         SÍ            loader.load_wizard_flags →
                                                     selfcheck (cobertura de flags)
  agent_business_context.json          no            referencia / documentación

Variable de entorno requerida:
  KB_PATH  →  ruta absoluta al archivo owasp_asi_knowledge_base.json
              ej. /app/kb/owasp_asi_knowledge_base.json

Secuencia de arranque que main.py debe seguir:
  1. kb.check_volume(kb_dir)          — verifica que el directorio y archivos existen
  2. kb.load(settings.kb_path)        — carga y valida el JSON contra los modelos
  3. kb.load_wizard_flags(kb_dir)     — lee los flags del wizard (coverage map)
  4. kb.selfcheck(loaded_kb, flags)   — coherencia interna del KB + cobertura wizard↔KB
  5. KBService(loaded_kb)             — construye el servicio de consulta

Si cualquiera de los cuatro primeros pasos falla, el contenedor no debe arrancar.

Secciones JSON requeridas en owasp_asi_knowledge_base.json:
  metadata, capability_taxonomy, threat_catalog, controls_catalog,
  assurance_methods, architecture_types, operational_capabilities,
  verdict_framework

Las secciones no listadas (playbooks, risk_catalog, cross_mapping,
registration_questionnaire, key_components, lifecycle_security,
agent_type_profiles) son ignoradas via extra="ignore" en KnowledgeBase.


ARCHIVOS
================================================================================

--------------------------------------------------------------------------------
models.py
--------------------------------------------------------------------------------
Modelos pydantic que representan la estructura del JSON del knowledge base.
Solo modela las secciones que el pipeline consume; ignora el resto via
extra="ignore" en KnowledgeBase.

Hallazgo importante: applicable_lifecycle_phases vive en el dominio (ControlDomain),
no en cada control individual. loader.py la inyecta en cada Control al cargar
mediante _inject_lifecycle_phases.

--------------------------------------------------------------------------------
loader.py
--------------------------------------------------------------------------------
Única función que toca el disco. Expone tres piezas:

  check_volume(kb_dir)
    Verifica la estructura del directorio del volumen antes de intentar cargar.
    Loguea cada archivo encontrado o ausente con nivel INFO/WARNING/ERROR.
    Lanza KBVolumeError si falta algún archivo requerido, indicando exactamente
    qué falta y dónde buscar la especificación.

    Salida en log (ejemplo con archivo requerido faltante):
      INFO  KB volume check — directory: /app/kb
      INFO    [OK]      owasp_asi_knowledge_base.json        (REQUIRED)
      ERROR   [MISSING] agent_validation_wizard.json         (REQUIRED)
      WARNING [ABSENT]  agent_business_context.json          (optional)

  load(path)
    Abre el JSON, verifica las secciones de nivel superior requeridas, valida
    contra los modelos pydantic y ejecuta _inject_lifecycle_phases.
    Lanza KBVolumeError si el JSON no es válido o le faltan secciones.
    Loguea un resumen al finalizar: versión, número de amenazas, controles y steps.

  KBVolumeError
    Excepción para ambos casos anteriores. main.py la captura y detiene el arranque.

--------------------------------------------------------------------------------
service.py
--------------------------------------------------------------------------------
La interfaz de consulta que los módulos del pipeline deben usar. Recibe el
KnowledgeBase cargado y expone métodos de alto nivel. Construye índices internos
al instanciarse para mantener las queries O(1)/O(n) simples.

  steps_for_flag(flag)                  → step_ids que contienen ese flag
  threats_for_step(step_id)             → T-IDs activados por el step
  maps_to_asi(threat_id)                → ASI-IDs via Appendix A (T9 devuelve [])
  oc_for_flag(flag)                     → OperationalCapability que referencia el flag
                                           (path especial critical_systems_access → OC-KC6.6)
  critical_controls_for_asi(asi_id)     → CTRL-IDs obligatorios según verdict_framework
  controls_mitigating(threat_id)        → controles que mitigan ese T-ID
  controls_for_phases(controls, phases) → filtra controles por lifecycle phases
  control_by_id(control_id)             → lookup de un control por su CTRL-ID
  high_risk_domains()                   → dominios de negocio de alto riesgo (EU AI Act)
  high_severity_risks()                 → ASI-IDs cuyo control faltante produce NOT_APT
  architecture_recommendations(arch_id) → prácticas + dominios para ese patrón
                                           (siempre incluye ARCH-CROSS como baseline)
  assurance_methods_for_asi(asi_id)     → ASSUR-IDs que cubren ese ASI
  kb_version()                          → versión del KB cargado

--------------------------------------------------------------------------------
selfcheck.py
--------------------------------------------------------------------------------
Validaciones de coherencia interna del KB que corren al arranque. Si alguna
falla, lanza KBSelfCheckError y la aplicación no arranca.

Verifica tres invariantes:
  1. activated_risks de cada STEP coincide con la derivación real vía
     threat_catalog.maps_to_asi (Appendix A). Este campo es un caché;
     cualquier desfase indica que el KB fue editado inconsistentemente.
  2. Todos los CTRL-IDs en critical_controls_by_risk existen en controls_catalog.
     Un ID huérfano haría que M5 construya un checklist con controles inexistentes.
  3. Cobertura de flags (wizard vs KB): los flags del wizard
     (coverage_validation.flag_coverage_map) coinciden con los cubiertos por el KB
     (capability_taxonomy STEPs + operational_capabilities). Requiere wizard_flags
     (pasados por main.py vía load_wizard_flags); si no se pasan, se omite.

--------------------------------------------------------------------------------
__init__.py
--------------------------------------------------------------------------------
Exporta todo lo que main.py necesita para inicializar el sistema:

  check_volume(kb_dir)  → verifica estructura del volumen; lanza KBVolumeError
  load(path)            → carga el KB desde disco; lanza KBVolumeError si falla
  selfcheck(kb)         → valida coherencia; lanza KBSelfCheckError si falla
  KBService             → clase de consulta que los módulos reciben como dependencia
  KBVolumeError         → excepción de estructura/carga del volumen
  KBSelfCheckError      → excepción de coherencia interna del KB

================================================================================
