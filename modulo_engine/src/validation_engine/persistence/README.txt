PERSISTENCE — Almacenamiento y recuperación de casos
================================================================================

El engine necesita guardar el AssessmentContext entre las dos fases de un caso:
después de run() (status = AWAITING_ASSURANCE) el contexto se persiste, y la API
lo recarga cuando llegan las attestations para llamar resume().

Sin persistencia el sistema no puede sobrevivir a reinicios ni gestionar múltiples
casos concurrentes.


DISEÑO
--------------------------------------------------------------------------------

El AssessmentContext completo se serializa como JSON y se guarda en una columna
JSONB de PostgreSQL. Este enfoque evita mapear todos los modelos pydantic a tablas
relacionales y es suficiente para Etapa 0.

Las columnas assessment_id, status, created_at y updated_at se almacenan también
como columnas propias (fuera del JSON) para permitir consultas eficientes sin
parsear el blob completo.

  assessments
  ┌─────────────────┬────────────┬────────────┬────────────┬──────────────┐
  │ assessment_id   │ status     │ created_at │ updated_at │ data (JSONB) │
  │ (PK, TEXT)      │ (TEXT idx) │ (TIMESTAMPTZ)│(TIMESTAMPTZ)│ (contexto) │
  └─────────────────┴────────────┴────────────┴────────────┴──────────────┘

La tabla se crea automáticamente al instanciar PostgresAssessmentStore si no existe.


FLUJO DE LLAMADAS
--------------------------------------------------------------------------------

  1. POST /assessments
       → orchestrator.run(ctx)          ← ejecuta M1–M5
       → store.save(ctx)                ← persiste (status = awaiting_assurance)
       → retorna assessment_id al cliente

  2. POST /assessments/{id}/attest
       → store.get(assessment_id)       ← recarga el contexto
       → ctx.assurance.attestations[ctrl_id] = Attestation(...)
       → store.update(ctx)              ← persiste las attestations

  3. POST /assessments/{id}/resume
       → store.get(assessment_id)       ← recarga el contexto
       → assurance_port.is_ready(ctx)   ← verifica que todas están
       → orchestrator.resume(ctx)       ← ejecuta M7 + Reporter
       → store.update(ctx)              ← persiste (status = completed)

  4. GET /assessments/{id}
       → store.get(assessment_id)       ← recarga y retorna el reporte


RELACIÓN CON LOS OTROS COMPONENTES
--------------------------------------------------------------------------------

  api/routes.py        →  llama save(), get(), update() en cada endpoint
  orchestrator.py      →  produce el ctx que se persiste; no llama al store
  contracts/context.py →  AssessmentContext serializado/deserializado aquí


ARCHIVOS
================================================================================

--------------------------------------------------------------------------------
store.py
--------------------------------------------------------------------------------
Define la interfaz AssessmentStore como Protocol @runtime_checkable.

  save(ctx) → None
    Persiste un caso nuevo. Se llama una sola vez por caso, justo después de
    orchestrator.run(). Si el assessment_id ya existe, el driver lanza IntegrityError.

  get(assessment_id) → AssessmentContext | None
    Carga un caso por su ID. Devuelve None si no existe (la API responde 404).

  update(ctx) → None
    Sobreescribe un caso existente: data, status y updated_at. Se llama después
    de cada attest y después de orchestrator.resume(). Lanza KeyError si no existe.

Es @runtime_checkable para que main.py pueda verificar en arranque que el store
pasado cumple la interfaz.

--------------------------------------------------------------------------------
sqlalchemy_store.py
--------------------------------------------------------------------------------
Implementación de AssessmentStore para PostgreSQL usando SQLAlchemy 2.x.

  _AssessmentRow (ORM model):
    Mapea la tabla assessments con los cinco campos descritos arriba.
    Usa mapped_column con tipado explícito (SQLAlchemy 2.x declarative style).
    La columna data es JSONB nativo de PostgreSQL (no TEXT con json.dumps manual).

  PostgresAssessmentStore.__init__(db_url):
    Crea el engine SQLAlchemy con pool_pre_ping=True (reconexión automática si
    Postgres reinicia). Llama create_all() para crear la tabla si no existe.

    Formato de db_url:
      postgresql+psycopg2://user:password@host:5432/nombre_bd

    Con Docker Compose, el host es el nombre del servicio Postgres definido
    en docker-compose.yml (ej. "db"), no "localhost".

  save(ctx):
    Serializa ctx con model_dump(mode="json") — convierte datetimes, enums y
    UUIDs a tipos JSON nativos — y crea un _AssessmentRow que inserta en la BD.

  get(assessment_id):
    Usa session.get() por clave primaria (lookup O(1) por índice PK).
    Reconstruye el AssessmentContext con model_validate(row.data): pydantic
    re-valida el JSON y reconstruye todos los modelos anidados.

  update(ctx):
    Lanza KeyError explícito si el ID no existe (evita silenciar un bug
    donde se intenta actualizar un caso que nunca fue guardado).

  Dependencias necesarias en pyproject.toml:
    sqlalchemy >= 2.0
    psycopg2-binary          ← driver que SQLAlchemy usa para hablar con Postgres

--------------------------------------------------------------------------------
__init__.py
--------------------------------------------------------------------------------
Exporta las dos piezas que main.py necesita:

  AssessmentStore         → para type hints e isinstance() checks
  PostgresAssessmentStore → instanciado en main.py con DB_URL del config

================================================================================