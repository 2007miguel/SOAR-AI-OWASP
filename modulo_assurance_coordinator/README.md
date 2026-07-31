# Assurance Coordinator

Módulo de orquestación de aseguramiento (M6) del sistema SOAR-AI-OWASP.  
Corre como un contenedor independiente y actúa como intermediario entre el engine y las fuentes de evidencia (humanas y automatizadas).

---

## Objetivo

Cuando el engine completa la fase de análisis (M1–M5) y el caso entra en estado `AWAITING_ASSURANCE`, el engine delega al coordinador la responsabilidad de recolectar toda la evidencia necesaria para que el pipeline pueda continuar hacia el veredicto (M7).

El coordinador es **invisible para el frontend**. El frontend siempre habla con el engine; el engine habla con el coordinador internamente.

---

## Valor en Etapa 1

En esta etapa inicial el coordinador cubre exclusivamente el flujo HITL (Human-In-The-Loop):

| Capacidad | Etapa 1 | Etapa 2+ |
|---|---|---|
| Recibir checklist del engine | SI | SI |
| Persistir attestaciones parciales | SI | SI |
| Detectar completitud y llamar resume | SI | SI |
| Lanzar conectores automatizados | NO (stubs) | SI |
| Normalizar resultados de herramientas | Minimal | Completo |

El beneficio inmediato es desacoplar la lógica de "¿están todas las attestaciones?" del engine, y dejar preparada la infraestructura para que los conectores se enchufen sin modificar nada del engine ni del coordinador.

---

## Flujo de comunicación

```
Engine                    Coordinator                 Engine (callback)
  |                            |                            |
  |-- POST /checklist -------->|                            |
  |                            | (crea sesión en DB)        |
  |                            |                            |
  |-- POST /attest/{id} ------>|                            |
  |   (reenvía cada HITL)      | (merge parcial)            |
  |                            |                            |
  |-- POST /attest/{id} ------>|                            |
  |                            | (is_ready = True)          |
  |                            |-- POST ENGINE_URL/resume ->|
  |                            |                            | (pipeline continúa)
```

El coordinador también expone `GET /status/{id}` para que el engine pueda hacer polling si lo necesita.

---

## Estructura de archivos

```
modulo_assurance_coordinator/
├── pyproject.toml
├── Dockerfile
├── .env.example
└── src/
    └── assurance_coordinator/
        ├── main.py
        ├── config.py
        ├── log_setup.py
        ├── contracts/
        │   ├── checklist.py
        │   ├── evidence.py
        │   └── jobs.py
        ├── persistence/
        │   └── job_store.py
        ├── attestation/
        │   ├── intake.py
        │   └── partial_store.py
        ├── checklist/
        │   └── presenter.py
        ├── connectors/
        │   ├── registry.py
        │   ├── selector.py
        │   ├── dispatcher.py
        │   └── client.py
        ├── normalizer/
        │   └── evidence_mapper.py
        └── port/
            └── assurance_api.py
└── tests/
    ├── conftest.py                # FakeStore en memoria (sin Postgres)
    ├── test_selector.py
    ├── test_normalizer.py
    └── test_attestation_intake.py
```

---

## Descripción por archivo

### Raíz del módulo

#### `pyproject.toml`
Manifiesto del paquete Python `assurance-coordinator`.  
Dependencias runtime: `fastapi`, `uvicorn`, `pydantic`, `pydantic-settings`, `sqlalchemy`, `psycopg2-binary`, `httpx`.

#### `Dockerfile`
Imagen basada en `python:3.12-slim`. Instala el paquete con `pip install -e .` y arranca con `uvicorn` en el puerto `8100`.

#### `.env.example`
Variables de entorno requeridas:

| Variable | Descripción |
|---|---|
| `ENGINE_URL` | URL base del engine para el callback de resume (ej. `http://engine:8000`) |
| `DB_URL` | Cadena de conexión al mismo PostgreSQL del engine |
| `LOG_LEVEL` | Nivel de log (`INFO` por defecto) |
| `PORT` | Puerto de escucha (`8100` por defecto) |

---

### `main.py`
Punto de entrada de la aplicación FastAPI.  
En el `lifespan` crea e inyecta en `app.state` todas las dependencias:
- `JobStore` (persistence)
- `AttestationIntake` (attestation)
- `PartialStore` (attestation)
- `ChecklistPresenter` (checklist)
- `ConnectorRegistry` + `ConnectorSelector` (connectors)
- `engine_url` (str)

Registra el router de `port/assurance_api.py` bajo el prefijo `/api/v1`.

#### `config.py`
`Settings` (pydantic-settings) — lee `DB_URL`, `ENGINE_URL`, `LOG_LEVEL`, `PORT` desde `.env` o variables de entorno del contenedor.

#### `log_setup.py`
`configure(level)` — inicializa `logging.basicConfig` apuntando a `stdout` con formato `timestamp [LEVEL] nombre — mensaje`. Nombrado `log_setup.py` para no colisionar con el módulo stdlib `logging`.

---

### `contracts/`

Modelos Pydantic compartidos entre los submódulos del coordinador. No contienen lógica de negocio.

#### `contracts/checklist.py`
- **`ChecklistItem`** — un control a evidenciar: `control_id`, `why` (ASI-IDs que lo requieren), `category`, `suggested_assur` (ASSUR-IDs recomendados).
- **`ChecklistBundle`** — lo que el engine envía al coordinador: `assessment_id`, `active_asi`, lista de `ChecklistItem`.

#### `contracts/evidence.py`
- **`AttestationStatus`** — enum: `implemented | partial | not_implemented`.
- **`AttestationInput`** — attestación de un control: `status`, `evidence` (texto libre), `assurance_method`.
- **`ToolResult`** — resultado de un conector automatizado: `connector`, `verdict`, `findings`, `raw_ref`.
- **`EvidenceBundle`** — paquete de evidencia completo al finalizar: attestaciones + tool_results + flags booleanos globales. Incluye las tres señales de veredicto que consume M7 del engine (`red_teaming_critical_findings`, `supply_chain_unverified`, `production_access`), alineadas con el `AssuranceLayer` del engine. Este es el contrato que se enviará al engine en la fase de conexión.

#### `contracts/jobs.py`
- **`JobStatus`** — enum: `pending | running | completed | failed`.
- **`ConnectorJob`** — trabajo de un conector: `job_id`, `assessment_id`, `connector`, `assur_id`, `status`, `result`, timestamps.

---

### `persistence/`

#### `persistence/job_store.py`
Capa de persistencia del coordinador sobre el mismo PostgreSQL del engine (tablas propias, sin tocar `assessments`).

**Tablas que crea en startup:**

| Tabla | Propósito |
|---|---|
| `coordinator_sessions` | Estado de la sesión de aseguramiento por `assessment_id`: checklist recibido, attestaciones parciales acumuladas, flags booleanos, status (`pending`/`ready`) |
| `connector_jobs` | Trabajos de conectores lanzados (vacío en Etapa 1) |

**Clase `JobStore`:**

| Método | Descripción |
|---|---|
| `create_session(assessment_id, active_asi, checklist)` | Crea la sesión cuando llega el checklist del engine |
| `get_session(assessment_id) → SessionData` | Devuelve un dataclass (no ORM row) con todo el estado actual |
| `update_attestations(assessment_id, new_attestations, **flags)` | Hace merge de las nuevas attestaciones sobre las existentes; usa `flag_modified` de SQLAlchemy para que JSONB detecte el cambio |
| `is_ready(assessment_id) → bool` | Verifica que todos los `control_id` del checklist tengan attestación |
| `mark_ready(assessment_id)` | Marca la sesión como `ready` |
| `create_job(job)` / `update_job(job_id, status, result)` | CRUD para connector_jobs (Etapa 2+) |

**`SessionData`** — dataclass de retorno de `get_session`. Al convertir la fila ORM a un dataclass antes de cerrar la sesión SQLAlchemy se evita el problema de atributos expirados fuera del contexto.

---

### `attestation/`

#### `attestation/intake.py`
**`AttestationIntake`** — punto de entrada para procesar una actualización de attestaciones HITL.

| Método | Descripción |
|---|---|
| `submit(assessment_id, attestations, incident_response_plan, red_teaming_done, assurance_methods_used) → bool` | Serializa las attestaciones, construye el dict de flags y delega a `JobStore.update_attestations`. Devuelve `True` cuando el caso está listo |

#### `attestation/partial_store.py`
**`PartialStore`** — vista de lectura sobre el estado parcial. Separa las responsabilidades de escritura (intake) y lectura (consultas semánticas).

| Método | Descripción |
|---|---|
| `get_pending(assessment_id) → list[str]` | Control-IDs que aún no tienen attestación |
| `build_bundle(assessment_id) → EvidenceBundle` | Construye el `EvidenceBundle` completo con el estado actual (para auditoría o para pasar al normalizer) |

---

### `checklist/`

#### `checklist/presenter.py`
**`ChecklistPresenter`** — helper interno de clasificación y formateo del checklist. Nunca es un endpoint público.

| Método | Descripción |
|---|---|
| `hitl_items(bundle) → list[ChecklistItem]` | Items que requieren attestación humana. En Etapa 1 retorna todos los items |
| `tool_items(bundle) → list[ChecklistItem]` | Items cubiertos por conectores automatizados. Retorna `[]` en Etapa 1 |
| `summary(bundle) → list[dict]` | Formato legible para logs y tracking interno: control_id, category, why, suggested_assur, needs_tool |

---

### `connectors/`

Los cuatro archivos de esta carpeta son **stubs** en Etapa 1. Su interfaz está definida para que Etapa 2 solo requiera implementar los métodos marcados con `NotImplementedError` y registrar los conectores en el registry.

#### `connectors/registry.py`
**`ConnectorRegistry`** — catálogo de conectores disponibles.  
- `list_connectors() → []`  
- `covers(assur_id) → []`  
*(Etapa 2: poblar con image names y sus ASSUR-IDs cubiertos.)*

#### `connectors/selector.py`
**`ConnectorSelector`** — mapea ASIs activos + ASSUR-IDs requeridos a la lista de conectores a ejecutar.  
- `select(active_asi, assur_ids) → []` — vacío hasta que el registry tenga entradas.

#### `connectors/dispatcher.py`
**`ConnectorDispatcher`** — lanza contenedores efímeros de conectores via Docker SDK o K8s Jobs.  
- `dispatch(connector, assessment_id, config) → job_id` — `NotImplementedError` en Etapa 1.

#### `connectors/client.py`
**`ConnectorClient`** — interfaz HTTP uniforme para llamar al endpoint `/run` de un conector en ejecución.  
- `run(base_url, target, config) → dict` — `NotImplementedError` en Etapa 1.

---

### `normalizer/`

#### `normalizer/evidence_mapper.py`
**`EvidenceMapper`** — normaliza salidas crudas de conectores al contrato `EvidenceBundle`.

| Método | Descripción |
|---|---|
| `build_bundle(assessment_id, attestations, tool_results, ...)` | Construye el `EvidenceBundle` tipado a partir de partes sueltas |
| `normalize_tool_result(raw, connector) → ToolResult` | Mapea un dict crudo de conector a `ToolResult`. Extensible: agregar un método por conector en Etapa 2 |

---

### `port/`

#### `port/assurance_api.py`
Router FastAPI principal. Define los tres endpoints HTTP que expone el coordinador y la función de callback al engine.

**Endpoints:**

| Método | Ruta | Llamado por | Descripción |
|---|---|---|---|
| `POST` | `/api/v1/checklist` | Engine | Recibe el `ChecklistBundle` cuando el caso entra en `AWAITING_ASSURANCE`. Crea la sesión en `coordinator_sessions`. Idempotente: si ya existe una sesión para ese `assessment_id` responde `409` en vez de sobrescribir attestaciones acumuladas |
| `POST` | `/api/v1/attest/{assessment_id}` | Engine | Reenvío de cada actualización HITL. Hace merge parcial. Si la sesión no existe responde `404`. En la transición `pending → ready` marca la sesión (`mark_ready`) y dispara el callback de resume **una sola vez**, en background (un engine lento/inaccesible no bloquea la respuesta) |
| `GET` | `/api/v1/status/{assessment_id}` | Engine (polling) | Devuelve `is_ready`, `pending_controls` y `status` (`pending`/`ready`) de la sesión |

**Callback interno:**

`_callback_resume(engine_url, assessment_id)` — ejecuta `POST {ENGINE_URL}/api/v1/assessments/{id}/resume` con `httpx`. Si el engine no responde o devuelve error HTTP, se registra en el log sin relanzar la excepción (el engine puede hacer polling con `GET /status` como fallback).

**DTOs locales:**

- `AttestRequest` — cuerpo del endpoint `/attest`: `attestations`, `incident_response_plan`, `red_teaming_done`, `assurance_methods_used`, y las tres señales de veredicto HITL alineadas con el engine: `red_teaming_critical_findings`, `supply_chain_unverified`, `production_access`. Los booleanos con valor `None` dejan el estado sin cambios (merge parcial).

---

## Tests

Los tests corren sin Postgres: `conftest.py` provee un `FakeStore` en memoria que imita la interfaz de `JobStore`, de modo que la lógica HITL (merge de attestaciones, `is_ready`, señales de veredicto) se verifica de forma aislada.

```
PYTHONPATH=src pytest tests/ -q
```

Cubren: selección de conectores (vacía en Etapa 1 + deduplicación), normalización de evidencia y presencia de las tres señales de veredicto en el `EvidenceBundle`, e intake de attestaciones (parcial → completo, persistencia de flags, merge con `None`).

---

## Base de datos

El coordinador comparte el mismo PostgreSQL del engine pero crea sus propias tablas. El engine sigue siendo el único dueño de la tabla `assessments`.

```
assessment-db (PostgreSQL)
├── assessments              ← engine (dueño exclusivo)
├── coordinator_sessions     ← coordinador
└── connector_jobs           ← coordinador
```

Las tablas se crean automáticamente en el startup del coordinador (`_Base.metadata.create_all`). No hay migraciones gestionadas en Etapa 1.

---

## Variables de entorno

Copiar `.env.example` → `.env` y ajustar:

```
ENGINE_URL=http://engine:8000
DB_URL=postgresql+psycopg2://postgres:changeme@db:5432/soar_db
LOG_LEVEL=INFO
PORT=8100
```

En Docker Compose el host de `DB_URL` es el nombre del servicio `db`, no `localhost`.

---

## Pendiente para Etapa 2

- Implementar `ConnectorRegistry.covers()` con el catálogo real de imágenes.
- Implementar `ConnectorDispatcher.dispatch()` usando el Docker SDK (`docker.from_env().containers.run()`).
- Implementar `ConnectorClient.run()` llamando al endpoint HTTP del contenedor efímero.
- Extender `EvidenceMapper.normalize_tool_result()` con lógica específica por conector.
- Agregar endpoint `POST /jobs/{job_id}/result` para que los conectores reporten su resultado.
- Gestionar migraciones con Alembic.
