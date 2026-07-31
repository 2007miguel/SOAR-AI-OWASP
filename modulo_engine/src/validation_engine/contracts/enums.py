from enum import Enum


class Status(str, Enum):
    INTAKE = "intake"
    ANALYZING = "analyzing"
    AWAITING_ASSURANCE = "awaiting_assurance"
    SCORING = "scoring"
    COMPLETED = "completed"
    ERROR = "error"


class VerdictResult(str, Enum):
    APT = "APT"
    APT_WITH_RESTRICTIONS = "APT_WITH_RESTRICTIONS"
    NOT_APT = "NOT_APT"


class AttestationStatus(str, Enum):
    IMPLEMENTED = "implemented"
    PARTIAL = "partial"
    NOT_IMPLEMENTED = "not_implemented"


class BusinessDomain(str, Enum):
    FINANCE = "Finance"
    HEALTHCARE = "Healthcare"
    EDUCATION = "Education"
    CRITICAL_INFRASTRUCTURE = "Critical Infrastructure"
    LEGAL = "Legal"
    LAW_ENFORCEMENT = "Law Enforcement"
    RETAIL = "Retail"
    TECHNOLOGY = "Technology"
    OTHER = "Other"


class ArchitectureId(str, Enum):
    SINGLE = "ARCH-SINGLE"
    CENTRAL = "ARCH-CENTRAL"
    SWARM = "ARCH-SWARM"


class LifecyclePhase(str, Enum):
    DESIGN = "design"
    BUILD = "build"
    RUNTIME = "runtime"
