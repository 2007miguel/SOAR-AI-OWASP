# tests_conexion_unit

Tests de integración para la capa de conexión entre el engine y el coordinator.

**No requieren Docker, Postgres ni red real.** Toda la infraestructura se reemplaza con implementaciones en memoria y mocks HTTP (`respx`). Corren en cualquier entorno con Python instalado.

---

## Contexto

El sistema tiene dos módulos independientes que se comunican por HTTP:

- **engine** (`modulo_engine/`) — pipeline determinista M1–M7. Corre el análisis OWASP, emite el checklist al coordinator y recibe el `EvidenceBundle` cuando el proceso de aseguramiento termina.
- **coordinator** (`modulo_assurance_coordinator/`) — plano de aseguramiento HITL. Recibe el checklist, acumula las attestaciones del evaluador humano y dispara el callback al engine cuando el caso está listo.

La capa de conexión que estos tests cubren es:

```
engine --[POST /checklist]--> coordinator   (al crear un assessment)
engine --[POST /attest/{id}]--> coordinator (forward de cada attestacion)
coordinator --[POST /resume/{id} + EvidenceBundle]--> engine  (callback al completarse)
```

---

## Estructura

```
tests_conexion_unit/
├── pyproject.toml                         -- configuracion pytest + dependencias
├── requirements.txt                       -- instalacion rapida con pip
├── conftest.py                            -- sys.path: hace importables ambos modulos
│
├── engine/
│   ├── conftest.py                        -- fixtures y fakes compartidos
│   ├── test_coordinator_adapter.py        -- Capa 1: CoordinatorAdapter (mock HTTP)
│   └── test_routes_coordinator_mode.py    -- Capa 2: rutas FastAPI en modo coordinator
│
└── coordinator/
    └── test_callback.py                   -- Capa 3: callback _callback_resume
```

---

## Capas de prueba

### Capa 1 — `test_coordinator_adapter.py` (7 tests)

Prueba `CoordinatorAdapter` en aislamiento total. Usa `respx` para interceptar las llamadas HTTP salientes sin llegar a la red.

| Test | Que verifica |
|---|---|
| `test_emit_checklist_posts_correct_payload` | El POST a `/checklist` lleva `assessment_id`, `active_asi` e `items` con los 4 campos requeridos por el coordinator |
| `test_emit_checklist_builds_local_checklist_before_posting` | El checklist se construye en `ctx.assurance.checklist` antes de enviarlo (la lista local queda poblada) |
| `test_emit_checklist_tolerates_409_idempotent` | Si el coordinator devuelve 409 (sesion ya existe), no se lanza excepcion — comportamiento idempotente |
| `test_emit_checklist_raises_502_when_coordinator_unreachable` | Si el coordinator no responde, `emit_checklist` lanza `HTTPException(502)` — fail-fast para evitar casos huerfanos |
| `test_forward_attestation_proxies_payload_verbatim` | El payload del engine llega intacto al coordinator sin modificaciones |
| `test_forward_attestation_propagates_coordinator_404` | Un 404 del coordinator se relanza como `HTTPException(404)` hacia el cliente del engine |
| `test_forward_attestation_raises_502_when_coordinator_unreachable` | Fallo de red al hacer forward se convierte en `HTTPException(502)` |

### Capa 2 — `test_routes_coordinator_mode.py` (8 tests)

Prueba las rutas FastAPI del engine usando `TestClient` de Starlette. La app de prueba se construye sin lifespan (sin KB real, sin Postgres) inyectando fakes directamente en `app.state`.

| Test | Que verifica |
|---|---|
| `test_attest_coordinator_calls_forward_attestation` | En modo coordinator, `/attest` delega al `CoordinatorAdapter.forward_attestation` |
| `test_attest_coordinator_does_not_write_to_local_store` | En modo coordinator, `/attest` NO escribe en el store local del engine — el coordinator es dueno de las attestaciones |
| `test_attest_coordinator_returns_coordinator_is_ready` | La respuesta de `/attest` refleja el `is_ready` que devuelve el coordinator, no una evaluacion local |
| `test_resume_coordinator_requires_evidence_bundle` | `/resume` sin body en modo coordinator devuelve 422 (el EvidenceBundle es obligatorio) |
| `test_resume_coordinator_populates_ctx_assurance_from_bundle` | El `EvidenceBundle` recibido en `/resume` popula correctamente `ctx.assurance` (attestations, flags) antes de que M7 corra |
| `test_resume_coordinator_m7_signals_propagate_from_bundle` | Los 3 signals de M7 (`red_teaming_critical_findings`, `supply_chain_unverified`, `production_access`) viajan del bundle a `ctx.assurance` |
| `test_resume_coordinator_returns_400_if_bundle_attestations_incomplete` | Si el bundle no tiene attestaciones para todos los controles criticos, `/resume` devuelve 400 |
| `test_resume_manual_mode_works_without_body` | Regresion: en modo manual (Etapa 0), `/resume` funciona sin body igual que antes de la conexion |

### Capa 3 — `test_callback.py` (5 tests)

Prueba la funcion `_callback_resume` del coordinator que dispara el POST al engine cuando el caso pasa a estado `ready`. Usa `respx` para interceptar la llamada al engine.

| Test | Que verifica |
|---|---|
| `test_callback_sends_attestations_in_body` | El callback envia las attestaciones como JSON body (no body vacio) con los campos correctos |
| `test_callback_sends_m7_verdict_signals` | Los 3 signals de M7 estan presentes en el payload enviado al engine |
| `test_callback_m7_signals_default_to_false_when_not_set` | Cuando no se configuran los signals, el payload los incluye como `false` (valores por defecto del EvidenceBundle) |
| `test_callback_does_not_raise_on_engine_connection_error` | Si el engine no responde, el callback no lanza excepcion — el error se loguea pero no interrumpe la tarea en background |
| `test_callback_does_not_raise_on_engine_http_error` | Si el engine devuelve un error HTTP (ej. 500), el callback tampoco lanza excepcion |

---

## Fakes utilizados

Definidos en `engine/conftest.py`, disponibles como fixtures de pytest:

| Clase | Que reemplaza | Comportamiento |
|---|---|---|
| `FakeStore` | `PostgresAssessmentStore` | Diccionario en memoria con `get/save/update` |
| `SpyOrchestrator` | `Orchestrator` | Ejecuta `resume()`, captura el ctx recibido y lo marca `COMPLETED/APT` |
| `FakeCoordinatorAdapter` | `CoordinatorAdapter` | Registra llamadas; devuelve `is_ready=False` por defecto |
| `FakeCoordinatorAdapter` (ready) | `CoordinatorAdapter` | Igual pero devuelve `is_ready=True` |
| `FakeManualAdapter` | `ManualAdapter` | Solo evalua `is_ready` en memoria, sin KB |

El `SpyOrchestrator` es clave para la Capa 2: captura el `ctx` que el engine le pasa justo antes de M7, permitiendo verificar que `ctx.assurance` fue populado correctamente con los datos del `EvidenceBundle`.

---

## Instalacion y ejecucion

```bash
# Desde esta carpeta (tests_conexion_unit/)
pip install -r requirements.txt

# Correr todos los tests
pytest

# Con detalle
pytest -v

# Solo una capa
pytest engine/test_coordinator_adapter.py -v
pytest engine/test_routes_coordinator_mode.py -v
pytest coordinator/test_callback.py -v
```

Resultado esperado: **20 passed** en menos de 5 segundos.

---

## Relacion con otros tests

| Suite | Ubicacion | Requiere infra | Que cubre |
|---|---|---|---|
| Golden tests engine | `modulo_engine/tests/` | No | Logica OWASP M1-M7, selfcheck KB |
| Unit tests coordinator | `modulo_assurance_coordinator/tests/` | No | Logica interna del coordinator (intake, normalizer, selector) |
| **Tests conexion unit** | `tests_conexion_unit/` (este folder) | No | Contratos y logica de la capa HTTP entre ambos modulos |
| Smoke test E2E | `tests_conexion_e2e/` | Si (Docker) | Flujo real con contenedores, Postgres y red |
