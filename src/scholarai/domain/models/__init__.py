"""Domain models, re-exported for convenient importing."""

from scholarai.domain.models.application import (
    Application,
    ApplicationStatus,
    Student,
)
from scholarai.domain.models.documents import (
    Achievement,
    Document,
    DocumentType,
    ExtractedApplicationData,
)
from scholarai.domain.models.evaluation import (
    ComponentScores,
    CriticResult,
    CriticVerdict,
    EvaluationResult,
    Recommendation,
)
from scholarai.domain.models.explainability import Evidence, EvidenceQuality
from scholarai.domain.models.human import HumanAction, HumanDecision
from scholarai.domain.models.results import (
    AcademicResult,
    AchievementResult,
    AgentResult,
    AgentStatus,
    EligibilityResult,
    FinancialResult,
    PolicyResult,
    VerificationResult,
)
from scholarai.domain.models.scholarship import (
    EligibilityRequirements,
    RecommendationThresholds,
    ScholarshipPreset,
    ScoringWeights,
)

__all__ = [
    "AcademicResult",
    "Achievement",
    "AchievementResult",
    "AgentResult",
    "AgentStatus",
    "Application",
    "ApplicationStatus",
    "ComponentScores",
    "CriticResult",
    "CriticVerdict",
    "Document",
    "DocumentType",
    "EligibilityRequirements",
    "EligibilityResult",
    "EvaluationResult",
    "Evidence",
    "EvidenceQuality",
    "ExtractedApplicationData",
    "FinancialResult",
    "HumanAction",
    "HumanDecision",
    "PolicyResult",
    "Recommendation",
    "RecommendationThresholds",
    "ScholarshipPreset",
    "ScoringWeights",
    "Student",
    "VerificationResult",
]
