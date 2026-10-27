"""Decision-model backends.

Every backend speaks the same *question schema*, which follows TypeSafe's
System One API because it is the de-facto convention that open models (Laya)
have adopted as well::

    questions = {
        "doc_type": {
            "type": "choice",
            "instructions": "What kind of document is `text`?",
            "criteria": {"invoice": "A request for payment", "other": None},
        },
        "urgent": {"type": "noul", "instructions": "Does `text` ask for urgent action?"},
        "tone": {
            "type": "score",
            "instructions": "How upset is the writer?",
            "criteria": ["Neutral", "Irritated", "Furious"],
        },
    }

and every backend returns answers in the same normalized shape::

    {
        "doc_type": {"type": "choice", "choice": "invoice", "confidence": 0.93,
                     "probabilities": {"invoice": 0.93, "other": 0.07}},
        "urgent":   {"type": "noul", "noul": 0.12},
        "tone":     {"type": "score", "score": 0.4, "confidence": 0.7,
                     "probabilities": {"0": 0.7, "1": 0.2, "2": 0.1},
                     "legend": {"0": "Neutral", "1": "Irritated", "2": "Furious"}},
    }

The library never depends on a vendor SDK; the hosted backend is a thin
``requests`` call so the dependency footprint stays small and the request
can be audited byte for byte.
"""

import json
import os
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional, Union

from .types import BackendError

Questions = Dict[str, Dict[str, Any]]
Answers = Dict[str, Dict[str, Any]]
State = Union[str, Dict[str, Any]]


@dataclass
class BackendResponse:
    """Normalized answer set returned by every backend."""

    answers: Answers
    model: str = ""
    request_id: Optional[str] = None
    usage: Dict[str, Any] = field(default_factory=dict)
    raw: Any = None


class DecisionBackend:
    """Interface every backend implements."""

    name: str = "base"

    def ask(self, state: State, questions: Questions) -> BackendResponse:
        raise NotImplementedError

    def close(self) -> None:  # pragma: no cover - trivial
        """Release any resources (HTTP sessions, loaded models)."""


class JevBackend(DecisionBackend):
    """TypeSafe AI's hosted Jev model, via ``POST /v1/systemone``.

    Works with any service exposing the same endpoint, which is why
    ``base_url`` is configurable (a self-hosted gateway, a proxy that adds
    logging, a mock server in CI).
    """

    name = "jev"
    DEFAULT_BASE_URL = "https://api.typesafe.ai"
    DEFAULT_MODEL = "jev-latest"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = 30.0,
        retries: int = 2,
        session: Any = None,
    ) -> None:
        self.api_key = api_key or os.getenv("TYPESAFE_API_KEY")
        if not self.api_key:
            raise BackendError(
                "Jev backend needs an API key: pass api_key= or set TYPESAFE_API_KEY"
            )
        self.model = model or os.getenv("TYPESAFE_MODEL", self.DEFAULT_MODEL)
        self.base_url = (
            base_url or os.getenv("TYPESAFE_BASE_URL", self.DEFAULT_BASE_URL)
        ).rstrip("/")
        self.timeout = timeout
        self.retries = max(0, int(retries))
        if session is None:
            import requests  # pylint: disable=import-outside-toplevel

            session = requests.Session()
        self._session = session

    @property
    def endpoint(self) -> str:
        return f"{self.base_url}/v1/systemone"

    def build_payload(self, state: State, questions: Questions) -> Dict[str, Any]:
        return {"model": self.model, "state": state, "questions": questions}

    def ask(self, state: State, questions: Questions) -> BackendResponse:
        payload = self.build_payload(state, questions)
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        last_error: Optional[Exception] = None
        for _ in range(self.retries + 1):
            try:
                response = self._session.post(
                    self.endpoint, json=payload, headers=headers, timeout=self.timeout
                )
            except Exception as err:  # pylint: disable=broad-except
                last_error = err
                continue
            if response.status_code in (429, 500, 502, 503, 504):
                last_error = BackendError(
                    f"HTTP {response.status_code}: {response.text[:200]}"
                )
                continue
            if response.status_code >= 400:
                raise BackendError(
                    f"Jev request failed with HTTP {response.status_code}: {response.text[:500]}"
                )
            try:
                data = response.json()
            except ValueError as err:
                raise BackendError(
                    f"Jev returned non-JSON body: {response.text[:200]}"
                ) from err
            answers = data.get("answers")
            if not isinstance(answers, dict):
                raise BackendError(f"Jev response has no 'answers' object: {data}")
            request_id = data.get("request_id") or response.headers.get("x-request-id")
            return BackendResponse(
                answers=answers,
                model=str(data.get("model", self.model)),
                request_id=request_id,
                usage=data.get("usage") or {},
                raw=data,
            )
        raise BackendError(
            f"Jev request failed after {self.retries + 1} attempts: {last_error}"
        )

    def close(self) -> None:
        try:
            self._session.close()
        except Exception:  # pylint: disable=broad-except
            pass


class LayaBackend(DecisionBackend):
    """Laya, the open-weight decision model, running locally.

    Requires the ``laya`` extra (``pip install rpaframework-decision[laya]``).
    The model is loaded lazily on first use, and kept in memory for the
    lifetime of the library (which is GLOBAL scope by default).
    """

    name = "laya"

    def __init__(
        self,
        model: Optional[str] = None,
        device: Optional[str] = None,
        preload: bool = True,
        **router_kwargs: Any,
    ) -> None:
        self.model = model or "convaiinnovations/laya"
        self.device = device
        self.preload = preload
        self.router_kwargs = router_kwargs
        self._router: Any = None

    def _get_router(self) -> Any:
        if self._router is None:
            try:
                import laya  # pylint: disable=import-outside-toplevel,import-error
            except ImportError as err:
                raise BackendError(
                    "Laya backend requires the 'laya' package: "
                    "pip install rpaframework-decision[laya]"
                ) from err
            kwargs = dict(self.router_kwargs)
            if self.device:
                kwargs["device"] = self.device
            kwargs.setdefault("preload", self.preload)
            self._router = laya.Router(**kwargs)
        return self._router

    def ask(self, state: State, questions: Questions) -> BackendResponse:
        router = self._get_router()
        try:
            raw = router.predict(state, questions)
        except Exception as err:  # pylint: disable=broad-except
            raise BackendError(f"Laya prediction failed: {err}") from err
        answers = raw.get("answers", raw) if isinstance(raw, dict) else raw
        normalized = {
            qid: _normalize_laya_answer(questions[qid], ans)
            for qid, ans in answers.items()
        }
        routing = raw.get("routing", {}) if isinstance(raw, dict) else {}
        return BackendResponse(
            answers=normalized,
            model=str(routing.get("model", self.model)),
            request_id=None,
            usage={},
            raw=raw,
        )


def _normalize_laya_answer(question: Dict[str, Any], answer: Any) -> Dict[str, Any]:
    """Map Laya's result dict onto the shared answer shape (best effort)."""
    qtype = question.get("type")
    if not isinstance(answer, dict):
        answer = {"value": answer}
    out: Dict[str, Any] = {"type": qtype}
    if qtype == "choice":
        out["choice"] = answer.get("choice") or answer.get("key") or answer.get("value")
        probs = answer.get("probabilities") or answer.get("distribution") or {}
        out["probabilities"] = probs
        conf = answer.get("confidence")
        if conf is None and probs:
            conf = max(probs.values())
        out["confidence"] = conf if conf is not None else 1.0
    elif qtype == "noul":
        out["noul"] = answer.get("noul", answer.get("probability", answer.get("value")))
    elif qtype == "score":
        out["score"] = answer.get(
            "score", answer.get("expected_level", answer.get("value"))
        )
        out["probabilities"] = answer.get("probabilities") or {}
        out["confidence"] = answer.get(
            "confidence",
            max(out["probabilities"].values()) if out["probabilities"] else 1.0,
        )
        out["legend"] = answer.get("legend") or {
            str(i): label for i, label in enumerate(question.get("criteria", []))
        }
    return out


class CallableBackend(DecisionBackend):
    """Wrap any Python callable ``(state, questions) -> answers``.

    Useful for tests, for deterministic fallbacks, and for plugging in a
    model the library does not know about yet without touching the library.
    """

    name = "callable"

    def __init__(
        self, func: Callable[[State, Questions], Any], model: str = "callable"
    ) -> None:
        self.func = func
        self.model = model

    def ask(self, state: State, questions: Questions) -> BackendResponse:
        raw = self.func(state, questions)
        if isinstance(raw, BackendResponse):
            return raw
        if not isinstance(raw, dict):
            raise BackendError("Callable backend must return a dict of answers")
        answers = raw.get("answers", raw)
        return BackendResponse(
            answers=answers, model=str(raw.get("model", self.model)), raw=raw
        )


class ReplayBackend(DecisionBackend):
    """Replay answers from a recorded audit log (JSON Lines) for dry runs.

    Each line is an :class:`~RPA.Decision.types.AuditRecord`; answers are
    matched by question text + options, in order of appearance.
    """

    name = "replay"

    def __init__(self, path: str) -> None:
        self.path = path
        self._records: Dict[str, list] = {}
        with open(path, "r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                record = json.loads(line)
                key = _replay_key(record.get("question", ""), record.get("options"))
                self._records.setdefault(key, []).append(record)
        self.model = "replay"

    def ask(self, state: State, questions: Questions) -> BackendResponse:
        answers: Answers = {}
        for qid, question in questions.items():
            key = _replay_key(question.get("instructions", ""), _options_of(question))
            bucket = self._records.get(key)
            if not bucket:
                raise BackendError(
                    f"No recorded answer for question {question.get('instructions')!r}"
                )
            record = bucket.pop(0)
            qtype = question.get("type")
            if qtype == "choice":
                answers[qid] = {
                    "type": "choice",
                    "choice": record["answer"],
                    "confidence": record.get("confidence", 1.0),
                    "probabilities": record.get("probabilities")
                    or {record["answer"]: 1.0},
                }
            elif qtype == "noul":
                answers[qid] = {
                    "type": "noul",
                    "noul": record.get("confidence", 1.0 if record["answer"] else 0.0),
                }
            else:
                probs = record.get("probabilities") or {}
                answers[qid] = {
                    "type": "score",
                    "score": record["answer"],
                    "confidence": record.get("confidence", 1.0),
                    "probabilities": probs,
                    "legend": {
                        str(i): label
                        for i, label in enumerate(question.get("criteria", []))
                    },
                }
        return BackendResponse(answers=answers, model="replay")


def _options_of(question: Dict[str, Any]) -> Any:
    criteria = question.get("criteria")
    if isinstance(criteria, dict):
        return list(criteria.keys())
    return criteria


def _replay_key(question: str, options: Any) -> str:
    return json.dumps([question, options], sort_keys=True, default=str)


BACKENDS = {
    "jev": JevBackend,
    "typesafe": JevBackend,
    "laya": LayaBackend,
    "callable": CallableBackend,
    "replay": ReplayBackend,
}


def create_backend(
    name: Union[str, DecisionBackend, Callable], **kwargs: Any
) -> DecisionBackend:
    """Instantiate a backend from a name, an instance or a bare callable."""
    if isinstance(name, DecisionBackend):
        return name
    if callable(name) and not isinstance(name, str):
        return CallableBackend(name, **kwargs)
    key = str(name).strip().lower()
    try:
        cls = BACKENDS[key]
    except KeyError as err:
        raise BackendError(
            f"Unknown decision backend {name!r}; available: {', '.join(sorted(BACKENDS))}"
        ) from err
    return cls(**kwargs)
