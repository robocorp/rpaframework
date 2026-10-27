"""Result types and exceptions for the RPA.Decision library.

Results are plain dataclasses that also support ``[]`` item access, so they
work with both ``${result.choice}`` and ``${result}[choice]`` in Robot
Framework, and serialize cleanly to JSON for work-item payloads.
"""

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Tuple


class DecisionError(Exception):
    """Base class for all errors raised by RPA.Decision."""


class BackendError(DecisionError):
    """The decision backend returned an error or an unusable response."""


class LowConfidenceError(DecisionError):
    """A decision was made, but its confidence is below the required threshold.

    The exception carries the full result so an ``EXCEPT`` branch in Robot
    Framework (or a Python ``except``) can still inspect what the model
    thought, log it, or route the item to a human.
    """

    def __init__(self, result: "ChoiceResult", threshold: float) -> None:
        self.result = result
        self.threshold = threshold
        super().__init__(
            f"Decision '{result.choice}' has confidence {result.confidence:.3f}, "
            f"below threshold {threshold:.3f} (question: {result.question!r})"
        )


class _ItemAccess:
    """Mixin so dataclass results can be indexed like dictionaries."""

    def __getitem__(self, key: str) -> Any:
        try:
            return getattr(self, key)
        except AttributeError as err:
            raise KeyError(key) from err

    def keys(self) -> List[str]:
        return list(asdict(self).keys())  # type: ignore[call-overload]

    def to_dict(self) -> Dict[str, Any]:
        """Return the result as a plain, JSON-serializable dictionary."""
        return asdict(self)  # type: ignore[call-overload]


@dataclass
class ChoiceResult(_ItemAccess):
    """Answer to a *choice* question: one option picked from a closed set.

    :attr choice: The winning option label.
    :attr confidence: How sure the model is about ``choice`` (0.0 - 1.0).
    :attr probabilities: Probability for **every** option, keyed by label.
    :attr question: The instructions that were asked.
    :attr options: The option labels that were allowed.
    :attr model: Resolved model identifier reported by the backend.
    :attr backend: Name of the backend that produced the answer.
    :attr request_id: Backend request id, when the backend reports one.
    :attr latency_ms: Wall-clock time of the backend call.
    """

    choice: str
    confidence: float
    probabilities: Dict[str, float]
    question: str = ""
    options: List[str] = field(default_factory=list)
    model: str = ""
    backend: str = ""
    request_id: Optional[str] = None
    latency_ms: float = 0.0

    def __str__(self) -> str:
        return self.choice

    def __bool__(self) -> bool:
        return bool(self.choice)

    def ranked(self) -> List[Tuple[str, float]]:
        """Options sorted from most to least probable."""
        return sorted(self.probabilities.items(), key=lambda kv: kv[1], reverse=True)

    def is_confident(self, threshold: float) -> bool:
        return self.confidence >= threshold


@dataclass
class CheckResult(_ItemAccess):
    """Answer to a yes/no question (a *noul* in TypeSafe's terminology).

    :attr probability: Calibrated probability that the proposition is true.
    :attr result: ``True`` when ``probability >= threshold``.
    :attr threshold: The threshold that was applied to produce ``result``.
    """

    probability: float
    result: bool
    threshold: float
    question: str = ""
    model: str = ""
    backend: str = ""
    request_id: Optional[str] = None
    latency_ms: float = 0.0

    def __str__(self) -> str:
        return str(self.result)

    def __bool__(self) -> bool:
        return self.result

    @property
    def is_uncertain(self) -> bool:
        """``True`` when the probability sits in the 0.35 - 0.65 band."""
        return 0.35 <= self.probability <= 0.65


@dataclass
class ScoreResult(_ItemAccess):
    """Answer to a *score* question: a position on an ordered rubric.

    :attr score: Probability-weighted level, may fall between levels
        (e.g. ``1.4`` on a 0 - 2 rubric).
    :attr level: The most probable integer level.
    :attr label: Human-readable label of ``level``.
    :attr confidence: Confidence in ``level``.
    :attr probabilities: Probability per level, keyed by integer level.
    :attr legend: Mapping from level to its label.
    """

    score: float
    level: int
    label: str
    confidence: float
    probabilities: Dict[int, float]
    legend: Dict[int, str]
    question: str = ""
    model: str = ""
    backend: str = ""
    request_id: Optional[str] = None
    latency_ms: float = 0.0

    def __str__(self) -> str:
        return self.label

    def __float__(self) -> float:
        return self.score

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        # JSON object keys must be strings.
        data["probabilities"] = {str(k): v for k, v in self.probabilities.items()}
        data["legend"] = {str(k): v for k, v in self.legend.items()}
        return data


@dataclass
class AuditRecord(_ItemAccess):
    """One entry in the library's audit log. Everything needed to replay,
    measure or explain a decision after the fact."""

    timestamp: str
    backend: str
    model: str
    kind: str  # choice | check | score | batch
    question: str
    options: Any
    answer: Any
    confidence: Optional[float]
    probabilities: Any
    threshold: Optional[float]
    accepted: Optional[bool]
    latency_ms: float
    request_id: Optional[str]
    state_digest: str
    state_chars: int
    usage: Dict[str, Any]
