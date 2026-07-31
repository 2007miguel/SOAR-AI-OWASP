from __future__ import annotations

from pydantic import BaseModel

from .enums import ArchitectureId, BusinessDomain, LifecyclePhase


class CapabilityFlags(BaseModel):
    # STEP-1 — Autonomy & reasoning
    autonomous_planning: bool = False
    goal_setting: bool = False
    self_evaluation: bool = False
    reflection_loops: bool = False
    adaptive_reasoning: bool = False

    # STEP-2 — Memory
    short_term_memory: bool = False
    long_term_memory: bool = False
    rag_access: bool = False
    shared_memory: bool = False
    vector_database: bool = False
    cross_session_context: bool = False
    knowledge_base: bool = False

    # STEP-3 — Tools & external access
    tool_use: bool = False
    api_access: bool = False
    code_execution: bool = False
    os_commands: bool = False
    filesystem_access: bool = False
    database_queries: bool = False
    web_browsing: bool = False
    mcp_server_integration: bool = False
    a2a_protocol: bool = False
    third_party_plugins: bool = False
    supply_chain_dependencies: bool = False
    critical_systems_access: bool = False  # path especial: OC-KC6.6, no en capability_taxonomy

    # STEP-4 — Identity & auth
    user_authentication: bool = False
    agent_identity: bool = False
    delegated_credentials: bool = False
    oauth_tokens: bool = False
    api_keys: bool = False
    inter_agent_trust: bool = False
    persistent_agent_identity: bool = False

    # STEP-5 — Human interaction
    human_interaction: bool = False
    human_in_the_loop: bool = False
    user_facing_interface: bool = False
    approval_workflows: bool = False
    natural_language_communication: bool = False
    persuasive_output: bool = False
    explainability_features: bool = False

    # STEP-6 — Multi-agent
    multi_agent_architecture: bool = False
    agent_orchestration: bool = False
    agent_delegation: bool = False
    swarm_architecture: bool = False
    central_orchestrator: bool = False
    peer_to_peer_agents: bool = False
    inter_agent_communication: bool = False
    agent_to_agent_trust: bool = False

    def active(self) -> dict[str, bool]:
        """Returns only the flags that are True."""
        return {k: v for k, v in self.model_dump().items() if v}


class BusinessContext(BaseModel):
    business_domain: BusinessDomain
    architecture_id: ArchitectureId
    lifecycle_phases: list[LifecyclePhase]


class Aibom(BaseModel):
    # CycloneDX document — informative in v1, not used for verdict derivation
    components: list[dict] = []
    metadata: dict = {}


class InputsLayer(BaseModel):
    capability_flags: CapabilityFlags = CapabilityFlags()
    business_context: BusinessContext
    aibom: Aibom | None = None
