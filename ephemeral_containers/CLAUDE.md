# Contenedores Efímeros — Contexto de Inicio de Sesión

Este archivo es el punto de entrada para continuar el desarrollo de los
contenedores efímeros de validación técnica del sistema SOAR-AI-OWASP.
Leer completo antes de cualquier implementación.

---

## El sistema completo — qué existe y qué está por construirse

**SOAR-AI-OWASP** es un sistema prescriptivo de cumplimiento OWASP para
agentes de IA. Dado un agente con capacidades declaradas, determina qué
controles de seguridad son obligatorios y produce un veredicto APT /
APT_WITH_RESTRICTIONS / NOT_APT.

### Módulos ya implementados y funcionando

```
modulo_engine/              FastAPI + Python. Motor determinista M1-M7.
modulo_assurance_coordinator/ Coordinador de assurance HITL.
modulo_frontend/            React + Vite. Wizard + checklist + veredicto.
```

**Stack del engine:** Python · FastAPI · Pydantic v2 · SQLAlchemy · Docker

**Flujo actual (funcionando):**
1. Usuario completa wizard (capability_flags + business_context + aibom opcional)
2. Engine corre M1-M7: threat mapping → risk mapping → control resolution → verdict
3. Checklist de controles OWASP requeridos devuelto al usuario
4. Usuario atestigua controles (status: implemented / partial / not_implemented)
5. Coordinator evalúa attestaciones y marca is_ready
6. Engine corre M7 + Reporter → veredicto final

**Enriquecimiento del KB ya implementado (sesión anterior):**
El checklist ahora devuelve nombre y descripción de cada control, nombre y
scope de cada ASI (why_detail), nombre de cada amenaza (threats_detail), y
nombre + herramientas de cada método de aseguramiento (suggested_assur_detail).
El reporte final incluye active_risks_detail y active_threats_detail con nombres.

---

## Dónde estamos — próximo paso: contenedores efímeros

Los contenedores efímeros son la capa de validación técnica automática.
Son instancias Docker de corta vida que el engine lanza después de un
assessment para ejecutar herramientas de seguridad reales contra el agente
bajo evaluación.

**Archivo de referencia obligatorio:**
`ephemeral_containers/plan_implementacion_herramientas.txt`

Ese archivo detalla a fondo el funcionamiento de cada herramienta, sus controles,
sus inputs, sus outputs, y la lógica de lanzamiento. Leerlo antes de implementar.

---

## Decisiones ya tomadas (no reabrir)

### Herramientas de primera entrega (5 tools)
| Herramienta | Controles | Por qué |
|---|---|---|
| OWASP ZAP | 9 | Contexto-agnóstico, Docker nativo, HTTP attacks |
| promptfoo | 3 | OWASP LLM Top 10 library incorporada, config mínima |
| Trivy | 3 | 100% agnóstico, escanea imagen/repo sin ejecutar el agente |
| Semgrep | 3 | SAST estático, rulesets preconfigurados |
| testssl.sh | 2 | TLS/mTLS, apunta a cualquier endpoint |

**AgentDojo fue descartado para primera entrega** — es un research framework
que requiere definir el entorno del agente, herramientas y escenarios de ataque
en Python. No es un tool CLI apuntable a cualquier API. Segunda fase.

### Cobertura de primera entrega
- 20 de 29 controles herramienta_tecnica (69%)
- Amenazas cubiertas: T1,T2,T3,T4,T5,T6,T7,T9,T11,T12,T13,T14,T15,T16,T17
- Sin cobertura en 1a entrega: T8 (requiere Langfuse), T10 (requiere AgentDojo)

### Datos requeridos — arquitectura de inputs
El request actual tiene: `capability_flags + business_context + aibom (opcional)`

Para los contenedores efímeros se necesitan dos fuentes adicionales:

**`target_config` (nuevo campo en request)** — configuración de deployment:
```json
{
  "agent_endpoint": "https://api.miagente.com",
  "agent_api_path": "/v1/chat",
  "auth_type": "bearer | api_key | none",
  "auth_value": "token-para-pruebas",
  "request_template": {"message": "{{input}}", "session_id": "test"},
  "response_path": "$.choices[0].message.content"
}
```
Usado por: ZAP, promptfoo, testssl.sh

**`aibom` (expandir schema existente)** — inventario de componentes:
- `container_image`: nombre de imagen Docker del agente
- `source_repo`: URL del repositorio de código fuente
- `dependencies`: contenido del manifiesto (requirements.txt, etc.)

Usado por: Trivy, Semgrep

Ambos campos son opcionales. Si no se proveen, las herramientas que los
necesitan reportan `"skipped — input not provided"` sin fallar el assessment.

### Qué se puede afirmar para primera entrega
- Infraestructura: TLS, mTLS, rate limiting, SSRF, SQLi, XSS (ZAP, testssl)
- Supply chain: CVEs en imagen, dependencias vulnerables, SBOM (Trivy)
- Código: patrones RCE, secrets hardcoded, CI/CD inseguro (Semgrep)
- LLM attacks: prompt injection, jailbreaks, PII leakage (promptfoo)
- Todos los resultados son deterministas — no dependen del dominio del agente

### Qué NO se afirma para primera entrega
- Validación de HITL → requiere AgentDojo (2da fase)
- Behavioral baseline → requiere Langfuse/SDK integration
- Memory poisoning cross-session → requiere AgentPoison (2da fase)
- System prompt hardening activo → requiere AgentFence (2da fase)
- Los 13 controles `revision_configuracion` → requieren contexto del deployment
- Los 6 controles `proceso_humano` → tabletop exercises, revisiones manuales

### Variabilidad — qué se puede y no se puede generalizar
Las herramientas de infraestructura (TLS, contenedores, SAST, deps) son
completamente contexto-agnósticas. Los payloads genéricos OWASP LLM Top 10
(promptfoo) también aplican a cualquier agente.

Lo que NO se puede generalizar automáticamente:
- Criterios de éxito/fallo específicos del dominio
- Tool-specific privilege escalation scenarios
- Behavioral baseline calibration
- Business logic violations

Esta es la razón por la que la primera entrega se enfoca en los 5 tools
agnósticos y deja AgentDojo para la segunda fase.

---

## Estructura de archivos de este módulo

```
ephemeral_containers/
├── CLAUDE.md                           ← este archivo
└── plan_implementacion_herramientas.txt ← spec detallada de los 5 tools
```

Lo que hay que crear (pendiente de implementación):
```
ephemeral_containers/
├── runner/                     Lógica Python que lanza los contenedores
│   ├── launcher.py             Selecciona y lanza herramientas según flags/aibom
│   ├── result_parser.py        Normaliza outputs JSON de cada herramienta
│   └── tool_configs/           Templates de config por herramienta
│       ├── zap_config.py       Genera ZAP config según flags activos
│       ├── promptfoo_config.py Genera promptfooconfig.yaml según flags
│       └── semgrep_config.py   Selecciona rulesets según flags
│
├── containers/                 Una carpeta por herramienta
│   ├── owasp_zap/
│   │   └── Dockerfile          (o usar imagen oficial directamente)
│   ├── promptfoo/
│   ├── trivy/
│   ├── semgrep/
│   └── testssl/
│
└── payloads/                   Biblioteca de ataques para promptfoo
    ├── prompt_injection.yaml   OWASP LLM Top 10 payloads
    ├── pii_leakage.yaml
    └── output_moderation.yaml
```

---

## Integración con el engine (cómo conecta con el código existente)

### Contrato existente relevante
El engine ya tiene `ToolResult` en `contracts/assurance.py`:
```python
class ToolResult(BaseModel):
    connector: str         # nombre de la herramienta
    control_id: str | None # control que validó
    asi: str | None        # ASI relacionado
    verdict: str           # "passed" | "failed" | "error" | "skipped"
    findings: list[dict]   # hallazgos detallados
    raw_ref: str | None    # referencia al output completo
```
Los resultados de los contenedores efímeros se mapean a esta estructura y
se guardan en `ctx.assurance.tool_results[]`.

### Punto de integración en el engine
El launcher de contenedores se invocaría desde:
- `routes.py: resume_assessment` — después de que M7 corre y el veredicto
  está generado, o en paralelo como capa adicional de validación.
- Alternativamente como endpoint separado: `POST /assessments/{id}/scan`
  que el usuario puede invocar explícitamente con target_config.

La decisión de si los tool_results afectan el veredicto o son solo informativos
está pendiente de definir. Recomendación: informativos en primera entrega
(no bloquean APT/NOT_APT), porque el veredicto ya tiene base sólida en M1-M7.

### Lógica de selección de herramientas (launcher.py)
```
SIEMPRE (si aibom.container_image):     Trivy image scan
SIEMPRE (si aibom.source_repo):          Trivy deps + Semgrep
SIEMPRE (si target_config.endpoint):     ZAP + promptfoo + testssl DATA-01

CONDICIONAL:
  database_queries=true  → ZAP SQLi rules
  web_browsing=true      → ZAP URL/SSRF rules
  delegated_credentials  → ZAP OAuth rules
  code_execution=true    → Semgrep eval/exec rules
  multi_agent_arch=true  → testssl mTLS (CTRL-INTERAGENT-01)
```

---

## KB — controles relevantes del CSV (referencia rápida)

El archivo de controles completo está en:
`archivos_desarrollo/controles/controles_paso5_validacion.csv`

Controles cubiertos por los 5 tools de primera entrega:

ZAP:        AUTH-01, AUTH-02, DATA-02, PROMPT-06, TOOL-03, TOOL-05,
            TOOL-07, TOOL-08, DEP-02
promptfoo:  DATA-06, PROMPT-01, PROMPT-03
Trivy:      SC-01, SC-02, DEP-01
Semgrep:    TOOL-06, SC-03, DEP-03
testssl:    DATA-01, INTERAGENT-01

Controles pendientes para 2da fase (behavioral tools):
AgentDojo:  DATA-04, PROMPT-04, TOOL-01, TOOL-03, TOOL-04, DEP-05
AgentFence: PROMPT-02, PROMPT-05
AgentPoison: DATA-04, DATA-05

---

## Estado del KB y enriquecimiento implementado

El KB (`modulo_engine/kb_volume/owasp_asi_knowledge_base.json`) tiene:
- `risk_catalog`: ASI01-ASI10 con title, scope, llm_top10_mapping (lista),
  aivss_core_risk, severity_drivers
- `threat_catalog`: T1-T17 con name, description, maps_to_asi
- `controls_catalog`: 8 dominios, 48 controles con name y description
- `assurance_methods`: ASSUR-01 a ASSUR-05 con name, description, tools[]
- `playbooks`: PB-01 a PB-06 (pendientes de exponer — segunda fase)
- `architecture_types`: ARCH-SINGLE/CENTRAL/SWARM/CROSS (pendiente)
- `key_components`: KC1-KC6 (pendiente)

Nota sobre el modelo del KB en `modulo_engine/src/validation_engine/kb/models.py`:
- `RiskEntry` usa `title` (no `name`) porque el JSON usa "title" para los ASIs
- `llm_top10_mapping` es `list[str]`, no `str`
- `KnowledgeBase` tiene `model_config = ConfigDict(extra="ignore")` — secciones
  no modeladas (playbooks, key_components, etc.) son ignoradas al cargar

---

## Decisiones pendientes para esta sesión

1. ¿Los tool_results de los contenedores afectan el veredicto o son solo
   informativos? (Recomendación: informativos en primera entrega)

2. ¿El scan se dispara automáticamente al completar el assessment, o es un
   endpoint separado que el usuario invoca explícitamente?

3. ¿Cómo se muestra en el frontend? (nueva sección en VerdictPanel mostrando
   resultado por control, o panel separado post-veredicto)

4. ¿Se expande el schema de `Aibom` en `contracts/inputs.py` para incluir
   `container_image` y `source_repo`, o se crea un campo `target_config`
   completamente separado?
