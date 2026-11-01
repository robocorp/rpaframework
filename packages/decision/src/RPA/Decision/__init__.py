import hashlib
import json
import logging
import time
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple, Union

from .backends import (
    BACKENDS,
    BackendResponse,
    CallableBackend,
    DecisionBackend,
    JevBackend,
    LayaBackend,
    ReplayBackend,
    create_backend,
)
from .types import (
    AuditRecord,
    BackendError,
    CheckResult,
    ChoiceResult,
    DecisionError,
    LowConfidenceError,
    ScoreResult,
)

__all__ = [
    "Decision",
    "ChoiceResult",
    "CheckResult",
    "ScoreResult",
    "AuditRecord",
    "DecisionError",
    "BackendError",
    "LowConfidenceError",
    "DecisionBackend",
    "JevBackend",
    "LayaBackend",
    "CallableBackend",
    "ReplayBackend",
    "BACKENDS",
]

OptionsType = Union[str, Sequence[str], Dict[str, Optional[str]]]
StateType = Union[str, Dict[str, Any]]


class Decision:
    """Library for making small, typed decisions with a *decision model*
    (also called a *System One* model) such as `Jev <https://typesafe.ai>`_
    or the open-weight `Laya <https://github.com/NandhaKishorM/laya>`_.

    Unlike a generative LLM, a decision model does not write text. You give it
    a *state* (the thing to look at) and a question with a **closed answer
    space**, and it returns one of the allowed answers together with a
    calibrated probability. That makes it a natural fit for the branch points
    of an automation:

    - routing work items (``invoice`` / ``credit note`` / ``reminder`` / ``junk``)
    - classifying failures (business exception vs. application exception)
    - guardrails before a side effect ("is it safe to auto-reply to this?")
    - deciding when to hand off to a human, using the confidence as the gate

    Three kinds of question are supported, mirroring the model APIs:

    ========  ===================================  ========================================
    Kind      Keyword                              Returns
    ========  ===================================  ========================================
    choice    ``Decide``, ``Decide Or Escalate``   one option + probability for every option
    yes/no    ``Check``                            probability that the proposition is true
    score     ``Score``                            position on an ordered rubric
    ========  ===================================  ========================================

    Every call is appended to an in-memory **audit log** (``Get Decision Audit
    Log``) and, optionally, to a JSON Lines file. Store those records in your
    work item payload: they are what you need to measure accuracy against
    ground truth later, and to explain a decision to an auditor.

    The library is **not** included in the ``rpaframework`` package. Add
    ``rpaframework-decision`` to your *conda.yaml* or *requirements.txt*.
    For the Laya backend use ``rpaframework-decision[laya]``.

    **Backends**

    ==========  ===================================================================
    ``jev``     TypeSafe's hosted model. Needs ``api_key`` or ``TYPESAFE_API_KEY``.
    ``laya``    Open-weight model running locally (CPU or CUDA). No data leaves
                the machine. Needs the ``laya`` extra.
    ``replay``  Replays answers from a saved audit log, for dry runs and tests.
    callable    Any Python ``(state, questions) -> answers`` function.
    ==========  ===================================================================

    **Robot Framework example usage**

    .. code-block:: robotframework

        *** Settings ***
        Library    RPA.Robocorp.Vault
        Library    RPA.Robocorp.WorkItems
        Library    RPA.Decision    threshold=0.85    audit_log=output/decisions.jsonl

        *** Tasks ***
        Route incoming documents
            ${secrets}=    Get Secret    TypeSafe
            Authorize To Jev    api_key=${secrets}[api_key]
            For Each Input Work Item    Route One Document

        *** Keywords ***
        Route One Document
            ${text}=    Get Work Item Variable    document_text
            ${decision}=    Decide    ${text}
            ...    question=What kind of document is this?
            ...    options=invoice=A request for payment, credit_note=A credit against an invoice, reminder, other
            Log    Routed as ${decision.choice} (${decision.confidence})
            IF    ${decision.confidence} < 0.85
                Set Work Item Variable    needs_review    ${True}
            END
            Set Work Item Variable    document_type    ${decision.choice}
            Set Work Item Variable    decision_audit    ${decision.to_dict()}
            Save Work Item

        Reply only when it is safe
            ${verdict}=    Check    ${email_body}
            ...    question=Is this a routine request that can be answered with a template?
            ...    threshold=0.9
            IF    ${verdict}
                Send Template Reply
            ELSE
                Create Output Work Item    variables={"reason": "manual"}
            END

        Escalate instead of guessing
            TRY
                ${choice}=    Decide Or Escalate    ${ticket}
                ...    question=Which team owns this ticket?
                ...    options=billing,technical,sales
                ...    threshold=0.9
            EXCEPT    LowConfidenceError*    type=glob
                Escalate To Human    ${ticket}
            END

    **Python example usage**

    .. code-block:: python

        from RPA.Decision import Decision, LowConfidenceError

        decide = Decision(backend="jev", api_key="...", threshold=0.85)

        result = decide.decide(
            invoice_text,
            question="What kind of document is this?",
            options={"invoice": "A request for payment", "credit_note": None, "other": None},
        )
        print(result.choice, result.confidence, result.probabilities)

        try:
            team = decide.decide_or_escalate(ticket, "Which team owns this?", ["billing", "tech"])
        except LowConfidenceError as err:
            route_to_human(ticket, err.result)

        # Local, offline alternative:
        local = Decision(backend="laya", device="cpu")
        ok = local.check(email, "Does the sender ask for a refund?")
        if ok:
            ...

    **Design notes**

    - Keep questions *about* the state and name the field you mean when the
      state is a dictionary: ``"Does `body` ask for a refund?"``.
    - Give options a one-line description when labels are ambiguous; the
      description is part of the prompt the model sees.
    - Decision models are strong on recognition and weak on arithmetic. Compute
      totals in Python; ask the model whether a document *is* an invoice, not
      whether its total is correct.
    - Treat the threshold as a business decision, tune it per use case from the
      audit log, and store the chosen value next to the decision.
    """  # noqa: E501

    ROBOT_LIBRARY_SCOPE = "GLOBAL"
    ROBOT_LIBRARY_DOC_FORMAT = "REST"

    def __init__(
        self,
        backend: Union[str, DecisionBackend, Callable, None] = None,
        threshold: float = 0.8,
        audit_log: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        **backend_options: Any,
    ) -> None:
        """
        :param backend: Backend name (``jev``, ``laya``, ``replay``), a backend
            instance, or a Python callable. ``None`` defers the choice until an
            ``Authorize To Jev`` / ``Use Laya`` / ``Set Decision Backend`` call.
        :param threshold: Default confidence required by ``Decide Or Escalate``
            and ``Require Confidence``.
        :param audit_log: Path to a JSON Lines file. When set, every decision is
            appended there as it happens.
        :param api_key: API key for hosted backends (``jev``).
        :param model: Model identifier override for the backend.
        :param base_url: Endpoint override for hosted backends.
        :param backend_options: Any other backend-specific options
            (for example ``device=cuda`` for ``laya``, ``timeout=10`` for ``jev``).
        """
        self.logger = logging.getLogger(__name__)
        self.threshold = float(threshold)
        self.audit_log_path = audit_log
        self.audit: List[AuditRecord] = []
        self._backend: Optional[DecisionBackend] = None
        if backend is not None:
            options = dict(backend_options)
            for key, value in (
                ("api_key", api_key),
                ("model", model),
                ("base_url", base_url),
            ):
                if value is not None:
                    options[key] = value
            self.set_decision_backend(backend, **options)

    # ------------------------------------------------------------------ setup

    @property
    def backend(self) -> DecisionBackend:
        if self._backend is None:
            raise DecisionError(
                "No decision backend configured. Call 'Authorize To Jev', "
                "'Use Laya' or 'Set Decision Backend' first."
            )
        return self._backend

    def set_decision_backend(
        self, backend: Union[str, DecisionBackend, Callable], **options: Any
    ) -> None:
        """Select the decision model backend used by all other keywords.

        :param backend: ``jev``, ``laya``, ``replay``, a backend instance,
            or a Python callable ``(state, questions) -> answers``.
        :param options: Backend-specific options. ``jev``: ``api_key``,
            ``model``, ``base_url``, ``timeout``, ``retries``. ``laya``:
            ``model``, ``device``, ``preload``. ``replay``: ``path``.

        Robot Framework example:

        .. code-block:: robotframework

            Set Decision Backend    laya    device=cpu
            Set Decision Backend    replay    path=recorded/decisions.jsonl
        """
        if self._backend is not None:
            self._backend.close()
        self._backend = create_backend(backend, **options)
        self.logger.info("Decision backend set to %r", self._backend.name)

    def authorize_to_jev(
        self,
        api_key: str,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = 30.0,
        retries: int = 2,
    ) -> None:
        """Use TypeSafe's hosted Jev model (or any ``/v1/systemone`` compatible
        endpoint).

        :param api_key: TypeSafe API key. Keep it in Vault, not in the robot.
        :param model: Model alias, default ``jev-latest``.
        :param base_url: Override the API host, e.g. for a logging proxy.
        :param timeout: HTTP timeout in seconds.
        :param retries: Retries on 429/5xx and connection errors.

        Robot Framework example:

        .. code-block:: robotframework

            ${secrets}=    Get Secret    TypeSafe
            Authorize To Jev    api_key=${secrets}[api_key]
        """
        self.set_decision_backend(
            "jev",
            api_key=api_key,
            model=model,
            base_url=base_url,
            timeout=timeout,
            retries=retries,
        )

    def use_laya(
        self,
        model: Optional[str] = None,
        device: Optional[str] = None,
        preload: bool = True,
    ) -> None:
        """Use the open-weight Laya model locally. Nothing leaves the machine.

        :param model: Hugging Face repo or local path, default ``convaiinnovations/laya``.
        :param device: ``cpu`` or ``cuda``; auto-detected when omitted.
        :param preload: Keep checkpoints in memory between calls (recommended
            for robots that make many decisions).

        Robot Framework example:

        .. code-block:: robotframework

            Use Laya    device=cpu
        """
        self.set_decision_backend("laya", model=model, device=device, preload=preload)

    def set_decision_threshold(self, threshold: float) -> float:
        """Change the default confidence threshold. Returns the previous value.

        :param threshold: A value between 0 and 1.
        """
        previous = self.threshold
        self.threshold = float(threshold)
        return previous

    # --------------------------------------------------------------- decisions

    def decide(
        self,
        state: StateType,
        question: str,
        options: OptionsType,
        threshold: Optional[float] = None,
    ) -> ChoiceResult:
        """Pick one option from a closed set.

        :param state: The text or dictionary the model should look at. A
            dictionary is sent as structured JSON; refer to its keys in the
            question with backticks, e.g. ``"What is `subject` about?"``.
        :param question: The question to answer, phrased so that exactly one
            of the options is the right answer.
        :param options: The allowed answers. Accepts a list of labels, a
            dictionary ``{label: description}`` (description may be ``None``),
            or a string: ``billing,technical,sales`` or
            ``billing=Payments and refunds,technical=Bugs and outages,other``.
        :param threshold: Only used for the ``accepted`` flag in the audit
            record; this keyword never fails on low confidence.
        :return: :class:`ChoiceResult` with ``choice``, ``confidence`` and
            ``probabilities``. Use ``${result.choice}`` in Robot Framework;
            ``${result}`` alone logs as the chosen label.

        Robot Framework example:

        .. code-block:: robotframework

            ${result}=    Decide    ${email_text}
            ...    question=Which team should handle this email?
            ...    options=billing=Invoices and refunds,technical=Bugs and outages,sales
            IF    ${result.confidence} >= 0.9
                Assign To    ${result.choice}
            ELSE
                Log    Unsure: ${result.probabilities}    level=WARN
            END
        """
        criteria = self._parse_options(options)
        response, latency = self._ask(
            state, {"q": self._choice_question(question, criteria)}
        )
        result = self._to_choice(response, "q", question, criteria, latency)
        effective = self.threshold if threshold is None else float(threshold)
        self._record(
            "choice",
            state,
            question,
            list(criteria),
            result.choice,
            result.confidence,
            result.probabilities,
            effective,
            result.confidence >= effective,
            response,
            latency,
        )
        self.logger.info(
            "Decided %r (%.3f) for: %s", result.choice, result.confidence, question
        )
        return result

    def decide_or_escalate(
        self,
        state: StateType,
        question: str,
        options: OptionsType,
        threshold: Optional[float] = None,
    ) -> ChoiceResult:
        """Like ``Decide``, but **fails** with ``LowConfidenceError`` when the
        confidence is below ``threshold`` (default: the library threshold).

        The error message carries the choice, the confidence and the
        threshold. The exception object (in Python) carries the full result
        as ``err.result``.

        Robot Framework example:

        .. code-block:: robotframework

            TRY
                ${type}=    Decide Or Escalate    ${text}
                ...    question=What kind of document is this?
                ...    options=invoice,credit_note,other
                ...    threshold=0.9
            EXCEPT    LowConfidenceError*    type=glob    AS    ${error}
                Log    ${error}    level=WARN
                Create Output Work Item    variables={"route": "manual_review"}
            END
        """
        effective = self.threshold if threshold is None else float(threshold)
        result = self.decide(state, question, options, threshold=effective)
        if result.confidence < effective:
            raise LowConfidenceError(result, effective)
        return result

    def check(
        self,
        state: StateType,
        question: str,
        threshold: float = 0.5,
        criteria_true: Optional[str] = None,
        criteria_false: Optional[str] = None,
    ) -> CheckResult:
        """Answer a yes/no question with a calibrated probability.

        :param state: The text or dictionary to look at.
        :param question: A proposition that is either true or false.
        :param threshold: Probability at or above which ``result`` is ``True``.
            Raise it (``0.9``) when a false positive is expensive, lower it
            when a false negative is.
        :param criteria_true: Optional description of what counts as *yes*.
        :param criteria_false: Optional description of what counts as *no*.
        :return: :class:`CheckResult`. ``${result}`` is truthy in ``IF``;
            ``${result.probability}`` is the raw probability.

        Robot Framework example:

        .. code-block:: robotframework

            ${safe}=    Check    ${email}
            ...    question=Is this a routine request that a template answers fully?
            ...    threshold=0.9
            IF    ${safe}    Send Template Reply    ${email}
        """
        q: Dict[str, Any] = {"type": "noul", "instructions": question}
        if criteria_true is not None or criteria_false is not None:
            q["criteria"] = {"true": criteria_true, "false": criteria_false}
        response, latency = self._ask(state, {"q": q})
        answer = self._answer(response, "q")
        probability = float(answer.get("noul", answer.get("probability", 0.0)))
        effective = float(threshold)
        result = CheckResult(
            probability=probability,
            result=probability >= effective,
            threshold=effective,
            question=question,
            model=response.model,
            backend=self.backend.name,
            request_id=response.request_id,
            latency_ms=latency,
        )
        self._record(
            "check",
            state,
            question,
            None,
            result.result,
            probability,
            None,
            effective,
            result.result,
            response,
            latency,
        )
        self.logger.info(
            "Checked %r -> %s (p=%.3f)", question, result.result, probability
        )
        return result

    def score(
        self,
        state: StateType,
        question: str,
        levels: Union[str, Sequence[str]],
    ) -> ScoreResult:
        """Place the state on an ordered rubric of 2 - 10 levels.

        :param state: The text or dictionary to look at.
        :param question: What is being rated.
        :param levels: Level labels from lowest to highest, as a list or a
            comma-separated string. Keep the labels descriptive; they are the
            rubric the model applies.
        :return: :class:`ScoreResult` with the weighted ``score``, the most
            probable integer ``level``, its ``label`` and per-level
            ``probabilities``.

        Robot Framework example:

        .. code-block:: robotframework

            ${tone}=    Score    ${complaint}
            ...    question=How upset is the customer?
            ...    levels=Calm,Irritated,Angry,Threatening to churn
            IF    ${tone.level} >= 2    Flag For Account Manager
        """
        labels = self._parse_levels(levels)
        q = {"type": "score", "instructions": question, "criteria": labels}
        response, latency = self._ask(state, {"q": q})
        answer = self._answer(response, "q")
        probs_raw = answer.get("probabilities") or {}
        probabilities = {int(k): float(v) for k, v in probs_raw.items()}
        legend_raw = answer.get("legend") or {
            str(i): label for i, label in enumerate(labels)
        }
        legend = {int(k): str(v) for k, v in legend_raw.items()}
        if probabilities:
            level = max(probabilities, key=probabilities.get)  # type: ignore[arg-type]
            confidence = float(answer.get("confidence", probabilities[level]))
        else:
            level = int(round(float(answer.get("score", 0))))
            confidence = float(answer.get("confidence", 1.0))
        weighted = answer.get("score")
        score_value = float(weighted) if weighted is not None else float(level)
        result = ScoreResult(
            score=score_value,
            level=level,
            label=legend.get(level, str(level)),
            confidence=confidence,
            probabilities=probabilities,
            legend=legend,
            question=question,
            model=response.model,
            backend=self.backend.name,
            request_id=response.request_id,
            latency_ms=latency,
        )
        self._record(
            "score",
            state,
            question,
            labels,
            result.score,
            confidence,
            {str(k): v for k, v in probabilities.items()},
            None,
            None,
            response,
            latency,
        )
        self.logger.info("Scored %r -> %s (%.2f)", question, result.label, result.score)
        return result

    def rank_options(
        self, state: StateType, question: str, options: OptionsType
    ) -> List[Tuple[str, float]]:
        """Return all options ordered from most to least probable.

        Handy when the top choice is not enough, e.g. to try candidates in
        order until one works, or to offer a human the best three.

        :return: List of ``(label, probability)`` pairs.

        Robot Framework example:

        .. code-block:: robotframework

            ${ranked}=    Rank Options    ${page_text}
            ...    question=Which link leads to the invoices page?
            ...    options=${link_texts}
            FOR    ${label}    ${prob}    IN    @{ranked}
                Log    ${label}: ${prob}
            END
        """
        result = self.decide(state, question, options)
        return result.ranked()

    def require_confidence(
        self,
        result: Union[ChoiceResult, CheckResult, ScoreResult],
        threshold: Optional[float] = None,
    ) -> None:
        """Fail with ``LowConfidenceError`` unless the given result meets the
        threshold. Lets you make the decision first, log it, and gate later.

        :param result: A result from ``Decide``, ``Check`` or ``Score``.
        :param threshold: Defaults to the library threshold.
        """
        effective = self.threshold if threshold is None else float(threshold)
        if isinstance(result, CheckResult):
            # For a yes/no answer "confidence" is distance from 0.5, rescaled to 0..1.
            confidence = abs(result.probability - 0.5) * 2
            as_choice = ChoiceResult(
                choice=str(result.result),
                confidence=confidence,
                probabilities={
                    "True": result.probability,
                    "False": 1 - result.probability,
                },
                question=result.question,
                model=result.model,
                backend=result.backend,
            )
        elif isinstance(result, ScoreResult):
            as_choice = ChoiceResult(
                choice=result.label,
                confidence=result.confidence,
                probabilities={str(k): v for k, v in result.probabilities.items()},
                question=result.question,
                model=result.model,
                backend=result.backend,
            )
        else:
            as_choice = result
        if as_choice.confidence < effective:
            raise LowConfidenceError(as_choice, effective)

    def ask_questions(
        self, state: StateType, questions: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Union[ChoiceResult, CheckResult, ScoreResult]]:
        """Ask several questions about the **same** state in one call.

        Batching questions that share a state is cheaper and faster than
        separate calls. Each question is a dictionary with ``type``
        (``choice`` / ``check`` / ``score``), ``question``, and ``options``
        (choice) or ``levels`` (score). Native backend question objects
        (``type: noul`` with ``instructions``) are also accepted as-is.

        :return: Dictionary keyed by question id with the matching result type.

        Robot Framework example:

        .. code-block:: robotframework

            &{type}=    Create Dictionary    type=choice
            ...    question=What kind of document is this?    options=invoice,other
            &{urgent}=    Create Dictionary    type=check
            ...    question=Does the document demand payment within 7 days?
            &{questions}=    Create Dictionary    doc_type=${type}    urgent=${urgent}
            ${answers}=    Ask Questions    ${text}    ${questions}
            Log    ${answers}[doc_type][choice] is urgent: ${answers}[urgent][result]
        """
        native: Dict[str, Dict[str, Any]] = {}
        meta: Dict[str, Tuple[str, str, Any, float]] = {}
        for qid, spec in questions.items():
            native[qid], meta[qid] = self._to_native_question(spec)
        response, latency = self._ask(state, native)
        results: Dict[str, Any] = {}
        for qid, (kind, question, extra, threshold) in meta.items():
            answer = self._answer(response, qid)
            if kind == "choice":
                results[qid] = self._to_choice(response, qid, question, extra, latency)
                self._record(
                    "choice",
                    state,
                    question,
                    list(extra),
                    results[qid].choice,
                    results[qid].confidence,
                    results[qid].probabilities,
                    threshold,
                    results[qid].confidence >= threshold,
                    response,
                    latency,
                )
            elif kind == "noul":
                probability = float(answer.get("noul", 0.0))
                results[qid] = CheckResult(
                    probability=probability,
                    result=probability >= threshold,
                    threshold=threshold,
                    question=question,
                    model=response.model,
                    backend=self.backend.name,
                    request_id=response.request_id,
                    latency_ms=latency,
                )
                self._record(
                    "check",
                    state,
                    question,
                    None,
                    results[qid].result,
                    probability,
                    None,
                    threshold,
                    results[qid].result,
                    response,
                    latency,
                )
            else:
                probs = {
                    int(k): float(v)
                    for k, v in (answer.get("probabilities") or {}).items()
                }
                legend = {
                    int(k): str(v) for k, v in (answer.get("legend") or {}).items()
                } or dict(enumerate(extra))
                level = max(probs, key=probs.get) if probs else int(round(float(answer.get("score", 0))))  # type: ignore[arg-type]
                results[qid] = ScoreResult(
                    score=float(answer.get("score", level)),
                    level=level,
                    label=legend.get(level, str(level)),
                    confidence=float(answer.get("confidence", probs.get(level, 1.0))),
                    probabilities=probs,
                    legend=legend,
                    question=question,
                    model=response.model,
                    backend=self.backend.name,
                    request_id=response.request_id,
                    latency_ms=latency,
                )
                self._record(
                    "score",
                    state,
                    question,
                    list(extra),
                    results[qid].score,
                    results[qid].confidence,
                    {str(k): v for k, v in probs.items()},
                    None,
                    None,
                    response,
                    latency,
                )
        return results

    def classify_items(
        self,
        items: Sequence[StateType],
        question: str,
        options: OptionsType,
        threshold: Optional[float] = None,
    ) -> List[ChoiceResult]:
        """Run ``Decide`` over a list of states and return one result per item.

        Items are decided one at a time so that a single failure does not lose
        the batch; the audit log records every item.

        Robot Framework example:

        .. code-block:: robotframework

            ${results}=    Classify Items    ${subjects}
            ...    question=Is this email subject about an order or something else?
            ...    options=order,other
            FOR    ${subject}    ${result}    IN ZIP    ${subjects}    ${results}
                Log    ${subject} -> ${result.choice}
            END
        """
        return [
            self.decide(item, question, options, threshold=threshold) for item in items
        ]

    # ------------------------------------------------------------------- audit

    def get_decision_audit_log(self) -> List[Dict[str, Any]]:
        """Return all decisions made so far as a list of dictionaries.

        Each record contains the question, options, answer, confidence,
        probabilities, threshold, whether it was accepted, latency, model and a
        digest of the state (never the state itself).
        """
        return [record.to_dict() for record in self.audit]

    def clear_decision_audit_log(self) -> int:
        """Forget the in-memory audit records. Returns how many were cleared.
        The JSON Lines file, if any, is left untouched."""
        count = len(self.audit)
        self.audit.clear()
        return count

    def save_decision_audit_log(self, path: str) -> str:
        """Write the in-memory audit records to ``path`` as JSON Lines.

        :return: The path written.

        Robot Framework example:

        .. code-block:: robotframework

            Save Decision Audit Log    ${OUTPUT_DIR}${/}decisions.jsonl
        """
        with open(path, "w", encoding="utf-8") as handle:
            for record in self.audit:
                handle.write(json.dumps(record.to_dict(), default=str) + "\n")
        return path

    # --------------------------------------------------------------- internals

    def _ask(
        self, state: StateType, questions: Dict[str, Dict[str, Any]]
    ) -> Tuple[BackendResponse, float]:
        prepared = self._prepare_state(state)
        started = time.perf_counter()
        response = self.backend.ask(prepared, questions)
        latency = (time.perf_counter() - started) * 1000
        return response, latency

    @staticmethod
    def _prepare_state(state: StateType) -> StateType:
        if isinstance(state, (str, dict)):
            return state
        if isinstance(state, (bytes, bytearray)):
            return state.decode("utf-8", errors="replace")
        return str(state)

    @staticmethod
    def _answer(response: BackendResponse, qid: str) -> Dict[str, Any]:
        try:
            answer = response.answers[qid]
        except KeyError as err:
            raise BackendError(
                f"Backend did not answer question {qid!r}: {response.answers}"
            ) from err
        if not isinstance(answer, dict):
            raise BackendError(f"Malformed answer for {qid!r}: {answer!r}")
        return answer

    @staticmethod
    def _choice_question(
        question: str, criteria: Dict[str, Optional[str]]
    ) -> Dict[str, Any]:
        return {"type": "choice", "instructions": question, "criteria": criteria}

    def _to_choice(
        self,
        response: BackendResponse,
        qid: str,
        question: str,
        criteria: Dict[str, Optional[str]],
        latency: float,
    ) -> ChoiceResult:
        answer = self._answer(response, qid)
        probabilities = {
            str(k): float(v) for k, v in (answer.get("probabilities") or {}).items()
        }
        choice = answer.get("choice")
        if choice is None and probabilities:
            choice = max(probabilities, key=probabilities.get)  # type: ignore[arg-type]
        if choice is None:
            raise BackendError(f"Backend returned no choice for {question!r}: {answer}")
        choice = str(choice)
        if choice not in criteria:
            # Be strict: an answer outside the allowed set is a protocol error,
            # not something to silently route on.
            raise BackendError(
                f"Backend chose {choice!r}, which is not one of {list(criteria)}"
            )
        confidence = answer.get("confidence")
        if confidence is None:
            confidence = probabilities.get(choice, 1.0)
        return ChoiceResult(
            choice=choice,
            confidence=float(confidence),
            probabilities=probabilities,
            question=question,
            options=list(criteria),
            model=response.model,
            backend=self.backend.name,
            request_id=response.request_id,
            latency_ms=latency,
        )

    def _to_native_question(
        self, spec: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], Tuple[str, str, Any, float]]:
        if "instructions" in spec and "question" not in spec:
            # Already in backend format.
            kind = spec.get("type", "choice")
            native = dict(spec)
            if kind == "choice":
                criteria = self._parse_options(
                    spec.get("criteria") or spec.get("options") or []
                )
                native["criteria"] = criteria
                return native, (
                    "choice",
                    spec["instructions"],
                    criteria,
                    self.threshold,
                )
            if kind == "noul":
                return native, (
                    "noul",
                    spec["instructions"],
                    None,
                    float(spec.get("threshold", 0.5)),
                )
            levels = self._parse_levels(spec.get("criteria") or [])
            native["criteria"] = levels
            return native, ("score", spec["instructions"], levels, 0.0)
        kind = str(spec.get("type", "choice")).lower()
        question = spec["question"]
        if kind in ("choice", "decide"):
            criteria = self._parse_options(spec.get("options") or [])
            threshold = float(spec.get("threshold", self.threshold))
            return self._choice_question(question, criteria), (
                "choice",
                question,
                criteria,
                threshold,
            )
        if kind in ("check", "noul", "bool", "boolean", "yesno"):
            native = {"type": "noul", "instructions": question}
            return native, ("noul", question, None, float(spec.get("threshold", 0.5)))
        if kind == "score":
            levels = self._parse_levels(spec.get("levels") or spec.get("options") or [])
            return {"type": "score", "instructions": question, "criteria": levels}, (
                "score",
                question,
                levels,
                0.0,
            )
        raise DecisionError(
            f"Unknown question type {kind!r}; use choice, check or score"
        )

    @staticmethod
    def _parse_options(options: OptionsType) -> Dict[str, Optional[str]]:
        if isinstance(options, dict):
            parsed = {
                str(k): (None if v in (None, "") else str(v))
                for k, v in options.items()
            }
        elif isinstance(options, str):
            parsed = {}
            for raw in options.split(","):
                raw = raw.strip()
                if not raw:
                    continue
                label, sep, desc = raw.partition("=")
                parsed[label.strip()] = desc.strip() if sep and desc.strip() else None
        else:
            parsed = {}
            for item in options:
                if isinstance(item, (list, tuple)) and len(item) == 2:
                    parsed[str(item[0])] = (
                        None if item[1] in (None, "") else str(item[1])
                    )
                else:
                    parsed[str(item)] = None
        if len(parsed) < 2:
            raise DecisionError("A choice needs at least two options")
        if len(parsed) > 255:
            raise DecisionError("A choice supports at most 255 options")
        return parsed

    @staticmethod
    def _parse_levels(levels: Union[str, Sequence[str]]) -> List[str]:
        if isinstance(levels, str):
            labels = [part.strip() for part in levels.split(",") if part.strip()]
        else:
            labels = [str(level) for level in levels]
        if not 2 <= len(labels) <= 10:
            raise DecisionError("A score needs between 2 and 10 levels")
        return labels

    def _record(  # pylint: disable=too-many-arguments
        self,
        kind: str,
        state: StateType,
        question: str,
        options: Any,
        answer: Any,
        confidence: Optional[float],
        probabilities: Any,
        threshold: Optional[float],
        accepted: Optional[bool],
        response: BackendResponse,
        latency: float,
    ) -> AuditRecord:
        prepared = self._prepare_state(state)
        serialized = (
            prepared
            if isinstance(prepared, str)
            else json.dumps(prepared, sort_keys=True, default=str)
        )
        record = AuditRecord(
            timestamp=datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
            backend=self.backend.name,
            model=response.model,
            kind=kind,
            question=question,
            options=options,
            answer=answer,
            confidence=confidence,
            probabilities=probabilities,
            threshold=threshold,
            accepted=accepted,
            latency_ms=round(latency, 2),
            request_id=response.request_id,
            state_digest=hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:16],
            state_chars=len(serialized),
            usage=dict(response.usage or {}),
        )
        self.audit.append(record)
        if self.audit_log_path:
            try:
                with open(self.audit_log_path, "a", encoding="utf-8") as handle:
                    handle.write(json.dumps(record.to_dict(), default=str) + "\n")
            except OSError as err:
                self.logger.warning(
                    "Could not append to audit log %s: %s", self.audit_log_path, err
                )
        return record
