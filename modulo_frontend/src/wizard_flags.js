export const FLAG_GROUPS = [
  {
    id: 'step1',
    label: 'STEP-1 — Autonomía y Razonamiento',
    flags: [
      { key: 'autonomous_planning',  label: 'Planificación autónoma' },
      { key: 'goal_setting',         label: 'Establecimiento de objetivos' },
      { key: 'self_evaluation',      label: 'Autoevaluación' },
      { key: 'reflection_loops',     label: 'Bucles de reflexión' },
      { key: 'adaptive_reasoning',   label: 'Razonamiento adaptativo' },
    ],
  },
  {
    id: 'step2',
    label: 'STEP-2 — Memoria',
    flags: [
      { key: 'short_term_memory',     label: 'Memoria a corto plazo' },
      { key: 'long_term_memory',      label: 'Memoria a largo plazo' },
      { key: 'rag_access',            label: 'Acceso RAG' },
      { key: 'shared_memory',         label: 'Memoria compartida entre agentes' },
      { key: 'vector_database',       label: 'Base de datos vectorial' },
      { key: 'cross_session_context', label: 'Contexto entre sesiones' },
      { key: 'knowledge_base',        label: 'Base de conocimiento interna' },
    ],
  },
  {
    id: 'step3',
    label: 'STEP-3 — Herramientas y Acceso Externo',
    flags: [
      { key: 'tool_use',                   label: 'Uso de herramientas' },
      { key: 'api_access',                 label: 'Acceso a APIs externas' },
      { key: 'code_execution',             label: 'Ejecución de código' },
      { key: 'os_commands',                label: 'Comandos del sistema operativo' },
      { key: 'filesystem_access',          label: 'Acceso al sistema de archivos' },
      { key: 'database_queries',           label: 'Consultas a bases de datos' },
      { key: 'web_browsing',               label: 'Navegación web' },
      { key: 'mcp_server_integration',     label: 'Integración con servidores MCP' },
      { key: 'a2a_protocol',               label: 'Protocolo agent-to-agent (A2A)' },
      { key: 'third_party_plugins',        label: 'Plugins de terceros' },
      { key: 'supply_chain_dependencies',  label: 'Dependencias de supply chain' },
      { key: 'critical_systems_access',    label: 'Acceso a sistemas críticos' },
    ],
  },
  {
    id: 'step4',
    label: 'STEP-4 — Identidad y Autenticación',
    flags: [
      { key: 'user_authentication',     label: 'Autenticación de usuarios' },
      { key: 'agent_identity',          label: 'Identidad del agente' },
      { key: 'delegated_credentials',   label: 'Credenciales delegadas' },
      { key: 'oauth_tokens',            label: 'Tokens OAuth' },
      { key: 'api_keys',                label: 'API keys' },
      { key: 'inter_agent_trust',       label: 'Confianza entre agentes' },
      { key: 'persistent_agent_identity', label: 'Identidad de agente persistente' },
    ],
  },
  {
    id: 'step5',
    label: 'STEP-5 — Interacción Humana',
    flags: [
      { key: 'human_interaction',              label: 'Interacción con humanos' },
      { key: 'human_in_the_loop',              label: 'Supervisión humana (HITL)' },
      { key: 'user_facing_interface',          label: 'Interfaz de usuario' },
      { key: 'approval_workflows',             label: 'Flujos de aprobación' },
      { key: 'natural_language_communication', label: 'Comunicación en lenguaje natural' },
      { key: 'persuasive_output',              label: 'Salidas persuasivas' },
      { key: 'explainability_features',        label: 'Características de explicabilidad' },
    ],
  },
  {
    id: 'step6',
    label: 'STEP-6 — Multi-agente',
    flags: [
      { key: 'multi_agent_architecture', label: 'Arquitectura multi-agente' },
      { key: 'agent_orchestration',      label: 'Orquestación de agentes' },
      { key: 'agent_delegation',         label: 'Delegación entre agentes' },
      { key: 'swarm_architecture',       label: 'Arquitectura de enjambre' },
      { key: 'central_orchestrator',     label: 'Orquestador central' },
      { key: 'peer_to_peer_agents',      label: 'Agentes peer-to-peer' },
      { key: 'inter_agent_communication', label: 'Comunicación entre agentes' },
      { key: 'agent_to_agent_trust',     label: 'Confianza agent-to-agent' },
    ],
  },
]

export const ALL_FLAG_KEYS = FLAG_GROUPS.flatMap(g => g.flags.map(f => f.key))

// Flags that should be auto-suggested based on architecture_id
export const ARCH_FLAG_SUGGESTIONS = {
  'ARCH-SINGLE':  [],
  'ARCH-CENTRAL': ['multi_agent_architecture', 'agent_orchestration', 'central_orchestrator'],
  'ARCH-SWARM':   ['multi_agent_architecture', 'swarm_architecture', 'peer_to_peer_agents', 'inter_agent_communication'],
}
