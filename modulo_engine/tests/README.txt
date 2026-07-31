TESTS — Suite de pruebas del engine (golden tests)
================================================================================

QUÉ ES
--------------------------------------------------------------------------------
Red de seguridad que "congela" el comportamiento correcto del motor. No cambia
ni el diseño ni el funcionamiento: solo se ACOPLA al código de src/ (lo lee y lo
ejercita, nunca lo modifica).

Sirve para que, si un cambio futuro rompe la traducción fiel a OWASP
(capability_flags -> STEPs -> amenazas -> riesgos ASI -> controles -> veredicto),
un test lo detecte al instante.


CÓMO SE EJECUTA
--------------------------------------------------------------------------------
Desde la carpeta modulo_engine/:

    pytest                 (o:  python -m pytest)

No requiere levantar el contenedor, ni la base de datos, ni la API. No afecta el
arranque del engine. Solo necesita la dependencia de test:

    pip install -e ".[test]"     (instala pytest)


DE DÓNDE SALEN LOS DATOS
--------------------------------------------------------------------------------
Los tests usan el KB REAL desarrollado para el sistema:
    archivos_desarrollo/knoledge_base_sistema/owasp_asi_knowledge_base.json
    archivos_desarrollo/Entradas_del_sistema/wizard/agent_validation_wizard.json

Se cargan en memoria aplicando la misma normalización de "staging" que hace el
volumen en despliegue (ver kb_volume.txt: security_practices objeto -> array).
Así los valores esperados reflejan exactamente lo que dice el KB, no algo
inventado. Si el KB cambia (nueva versión OWASP), algunos golden tests fallarán
a propósito, obligando a revisar el cambio de forma consciente.


ESTRUCTURA (espejo de estructura_engine.txt §2)
--------------------------------------------------------------------------------
  tests/
    conftest.py                 Fixtures compartidos: KB real (kb / raw_kb),
                                 flags del wizard, orquestador. Pone src/ y
                                 tests/ en el path (no hace falta instalar).
    fixtures/inputs.py          Constructores de inputs de ejemplo
                                 (flags, business_context, context).
    kb/
      test_selfcheck.py         El KB es coherente con OWASP: activated_risks =
                                 derivación del Appendix A, sin controles
                                 huérfanos, cobertura de flags wizard-vs-KB, y
                                 T9 sin ASI. También comprueba que un desajuste
                                 FALLA el arranque.
    modules/                    Un archivo por módulo, testeado en aislamiento:
      test_m1_intake.py         Validación de inputs (error bloqueante vs warning).
      test_m2_threat_mapper.py  Golden: flags -> STEPs -> amenazas (T-IDs);
                                 incluye la vía especial OC-KC6.6.
      test_m3_risk_mapper.py    Golden: flags -> ASI (el ancla de fidelidad).
      test_m4_escalator.py      Dominio de alto riesgo; la arquitectura NUNCA
                                 cambia los ASI (invariante I3).
      test_m5_control_resolver.py  Controles críticos por ASI; CTRL-MON-01
                                 siempre presente; CTRL-DEP-05 por alto riesgo.
      test_m7_verdict_engine.py Los 3 veredictos y las 5 condiciones de NOT_APT;
                                 M7 escribe verdict, no status.
    orchestrator/
      test_full_validation.py   Flujo completo end-to-end con attestación manual:
                                 crear -> pausa -> attestar -> reanudar ->
                                 veredicto; transiciones de estado del
                                 orquestador; reproducibilidad; aborto en M1.


QUÉ NO CUBRE (por diseño de esta etapa)
--------------------------------------------------------------------------------
  - La capa api/ (FastAPI) y persistence/ (Postgres): no se ejercitan aquí para
    mantener los tests deterministas y sin dependencias externas.
  - El plano de aseguramiento real (conectores/herramientas): pertenece a otros
    contenedores (Etapas 1-2), fuera del engine.


REGLA
--------------------------------------------------------------------------------
Los tests solo se ACOPLAN. Si un test falla, primero se revisa si el cambio de
código o de KB era intencional; el objetivo es que ninguna modificación rompa la
fidelidad a OWASP sin que alguien lo note.

================================================================================
