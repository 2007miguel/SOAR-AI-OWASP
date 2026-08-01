# tests_conexion_e2e

Smoke test end-to-end para la capa de conexion entre el engine y el coordinator.

**Requiere los tres contenedores corriendo** (engine, coordinator, db). Realiza llamadas HTTP reales contra los servicios, verifica respuestas reales y comprueba que el flujo completo funciona sobre Postgres con datos persistidos.

---

## Contexto

Una vez que los tests unitarios de `tests_conexion_unit/` verifican que la logica de la conexion es correcta, este smoke test verifica que el sistema **armado y corriendo** se comporta igual: que los contenedores se comunican entre si, que los datos se persisten en Postgres y que el ciclo de vida completo de un caso produce un veredicto real.

El flujo que valida es:

```
[Usuario/Script]
      |
      v
POST /assessments  (engine:8000)
      |-- M1 a M5 internamente
      |-- POST /checklist --> coordinator:8100  (sesion creada)
      |
      v
POST /attest/{id}  (engine:8000)
      |-- forward --> POST /attest/{id} --> coordinator:8100  (attestacion acumulada)
      |
      v  (al completarse todos los controles)
coordinator --> POST /resume/{id} + EvidenceBundle --> engine:8000
      |-- M7 corre con los datos del bundle
      |
      v
GET /assessments/{id}  (engine:8000)
      |-- veredicto: APT / APT_WITH_RESTRICTIONS / NOT_APT
```

---

## Prerequisitos

### 1. Contenedores corriendo

Desde `modulo_engine/`:

```powershell
docker compose up -d
```

Esto levanta tres servicios:
- `engine` en `localhost:8000` — motor determinista OWASP
- `coordinator` en `localhost:8100` — plano de aseguramiento HITL
- `db` en `localhost:5432` — Postgres compartido

Verificar que estan sanos:

```powershell
docker compose ps
# Los tres deben mostrar "running" o "healthy"
```

### 2. PowerShell disponible

El script usa `Invoke-RestMethod` que esta disponible en PowerShell 5.1+ (Windows) y PowerShell 7+ (Windows/Linux/Mac).

---

## Ejecucion

```powershell
# Desde esta carpeta (tests_conexion_e2e/)
.\smoke_test_conexion.ps1
```

El script verifica primero que ambos servicios responden. Si alguno no esta disponible, termina con error antes de ejecutar los tests.

Resultado esperado:

```
=== PREREQUISITOS ===
  [OK] Engine responde en http://localhost:8000/api/v1
  [OK] Coordinator responde en http://localhost:8100/api/v1

=== BLOQUE 1: Flujo feliz (APT) ===
  ...
  [PASS] veredicto = APT

=== BLOQUE 2: Signals M7 (NOT_APT forzado) ===
  ...
  [PASS] veredicto = NOT_APT

=== BLOQUE 3: Casos de error ===
  ...

=====================================================
 RESULTADO: 22 pasados  /  0 fallidos
=====================================================
```

---

## Bloques de prueba

### Bloque 1 — Flujo feliz completo (13 checks, veredicto APT)

Recorre el ciclo de vida completo de un caso con todos los controles implementados y sin signals de riesgo. Verifica cada paso de la integracion:

| Paso | Endpoint | Que verifica |
|---|---|---|
| 1.1 | `POST /assessments` (engine) | Status `awaiting_assurance`, checklist no vacio, `assessment_id` asignado |
| 1.2 | `GET /status/{id}` (coordinator) | Sesion creada automaticamente por el engine, `pending` con todos los controles |
| 1.3 | `POST /attest` parcial (engine) | `is_ready=false` con controles pendientes; el forward al coordinator funciona |
| 1.4 | `POST /attest` completo (engine) | `is_ready=true` al cubrir todos los controles criticos |
| 1.5 | `GET /assessments/{id}` (engine) | Status `completed`, veredicto `APT` tras el callback del coordinator |
| 1.6 | `GET /status/{id}` (coordinator) | Sesion marcada `ready` en el coordinator |

### Bloque 2 — Signals M7: NOT_APT forzado (3 checks)

Crea un segundo caso donde se attestan todos los controles como `implemented` pero se activan los signals de riesgo que M7 usa para decidir NOT_APT:

- `supply_chain_unverified = true` — componentes del supply chain sin verificar
- `production_access = true` — el agente tiene acceso directo a produccion

Ambos signals combinados activan la condicion NOT_APT (d) del VerdictEngine. El veredicto final debe ser `NOT_APT` aunque todos los controles esten marcados como implementados, lo que prueba que el `EvidenceBundle` enviado por el coordinator llega correctamente a M7.

### Bloque 3 — Casos de error (6 checks)

Verifica que el sistema rechaza operaciones invalidas con el codigo HTTP correcto:

| Caso | Endpoint | Codigo esperado | Razon |
|---|---|---|---|
| Assessment inexistente | `GET /assessments/id-falso` | 404 | El ID no existe en Postgres |
| Attest sobre caso completado | `POST /attest/{id}` (completed) | 409 | El caso ya no esta en `awaiting_assurance` |
| Resume sin EvidenceBundle | `POST /resume/{id}` (sin body) | 422 | En modo coordinator el bundle es obligatorio |
| Checklist duplicado | `POST /checklist` (coordinator) | 409 | La sesion del coordinator ya existe para ese assessment |

---

## Diferencias con los tests unitarios

| Aspecto | `tests_conexion_unit/` | `tests_conexion_e2e/` (este folder) |
|---|---|---|
| Infraestructura | Ninguna (fakes en memoria) | 3 contenedores Docker + Postgres |
| HTTP | Interceptado con `respx` | Real entre servicios |
| Persistencia | Diccionario en memoria | Postgres con tablas reales |
| Velocidad | ~3 segundos | ~15 segundos (incluye waits del callback) |
| Cuando falla | Hay un bug en la logica | Hay un problema de integracion, red o configuracion |
| Como ejecutar | `pytest` | `.\smoke_test_conexion.ps1` |

Ambas suites son complementarias: los tests unitarios protegen la logica ante regresiones rapidas; el smoke test E2E confirma que el sistema desplegado se comporta correctamente de extremo a extremo.

---

## Datos de prueba

El script usa un conjunto fijo de `capability_flags` que activa los siguientes riesgos OWASP:

- Flags activos: `web_browsing`, `code_execution`, `file_system_access`, `external_api_calls`, `memory_persistence`, `multi_agent_coordination`, `user_data_access`, `multi_agent_architecture`, `inter_agent_communication`
- ASIs derivados: ASI02, ASI03, ASI04, ASI05, ASI06, ASI07, ASI10
- Dominio: Technology (no es dominio de alto riesgo)
- Controles criticos resultantes: ~23 controles (varia segun version del KB)

El Bloque 2 reutiliza el mismo input base pero modifica los signals en el attest para forzar NOT_APT.

---

## Solucion de problemas

**El script dice "Engine no disponible"**
Los contenedores no estan corriendo o aun estan iniciando. Ejecutar `docker compose up -d` desde `modulo_engine/` y esperar unos segundos.

**Falla el paso 1.5 (veredicto no aparece)**
El callback del coordinator al engine puede tardar mas de 3 segundos en un sistema lento. Aumentar el `Start-Sleep -Seconds 3` a 5 o mas en el script.

**Falla con NOT_APT en Bloque 1**
El KB o la logica de M7 cambiaron. Verificar que los 3 signals de M7 (`supply_chain_unverified`, `production_access`, `red_teaming_critical_findings`) esten en `false` en el attest del Bloque 1.

**Error de conexion entre engine y coordinator**
Verificar que ambos servicios estan en la misma red Docker (`docker network inspect modulo_engine_default`). El coordinator debe resolver el hostname `engine` y el engine debe resolver `coordinator`.
