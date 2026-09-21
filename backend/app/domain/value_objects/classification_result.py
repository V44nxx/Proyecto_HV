"""
Classification result value object.
"""

from dataclasses import dataclass, field
from typing import Any

from app.config.constants import DocumentType


@dataclass(frozen=True)
class ClassificationResult:
    """
    Immutable value object representing the outcome of document classification.
    """
    document_type: DocumentType
    confidence: float
    matched_indicators: list[str] = field(default_factory=list)
    scores: dict[str, float] = field(default_factory=dict)
    detected_sections: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)

    @property
    def is_definitive(self) -> bool:
        """True if the classification is confident and not UNKNOWN."""
        return self.document_type != DocumentType.UNKNOWN and self.confidence >= 0.50

    def to_dict(self) -> dict[str, Any]:
        """Serialize value object to dictionary."""
        return {
            "document_type": self.document_type.value if hasattr(self.document_type, "value") else str(self.document_type),
            "confidence": round(self.confidence, 4),
            "matched_indicators": list(self.matched_indicators),
            "scores": {k: round(v, 4) for k, v in self.scores.items()},
            "detected_sections": list(self.detected_sections),
            "reasons": list(self.reasons),
            "is_definitive": self.is_definitive,
        }
