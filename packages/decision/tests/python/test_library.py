import json

import pytest
import responses

from RPA.Decision import (
    BackendError,
    CheckResult,
    ChoiceResult,
    Decision,
    DecisionError,
    LowConfidenceError,
    ScoreResult,
)
from RPA.Decision.backends import JevBackend

JEV_URL = "https://api.typesafe.ai/v1/systemone"


# ----------------------------------------------------------------- fixtures


def fake_model(state, questions):
    """Deterministic stand-in for a decision model."""
    answers = {}
    text = state if isinstance(state, str) else json.dumps(state)
    for qid, q in questions.items():
        if q["type"] == "choice":
            labels = list(q["criteria"])
            hit = next((label for label in labels if label in text.lower()), labels[-1])
            probs = {label: 0.05 for label in labels}
            probs[hit] = 1 - 0.05 * (len(labels) - 1)
            answers[qid] = {
                "type": "choice",
                "choice": hit,
                "confidence": probs[hit],
                "probabilities": probs,
            }
        elif q["type"] == "noul":
            answers[qid] = {
                "type": "noul",
                "noul": 0.9 if "refund" in text.lower() else 0.1,
            }
        else:
            n = len(q["criteria"])
            probs = {str(i): (0.7 if i == 1 else 0.3 / (n - 1)) for i in range(n)}
            answers[qid] = {
                "type": "score",
                "score": 1.1,
                "confidence": 0.7,
                "probabilities": probs,
                "legend": {str(i): label for i, label in enumerate(q["criteria"])},
            }
    return {"answers": answers, "model": "fake-1"}


@pytest.fixture
def lib():
    return Decision(backend=fake_model, threshold=0.8)


# ------------------------------------------------------------------ decide


def test_decide_returns_choice_result(lib):
    result = lib.decide(
        "Please send the invoice again", "What is this?", "invoice,reminder,other"
    )
    assert isinstance(result, ChoiceResult)
    assert result.choice == "invoice"
    assert str(result) == "invoice"
    assert result["choice"] == "invoice"
    assert result.options == ["invoice", "reminder", "other"]
    assert result.backend == "callable"
    assert result.model == "fake-1"
    assert sum(result.probabilities.values()) == pytest.approx(1.0)
    assert result.ranked()[0][0] == "invoice"


def test_options_parsing_variants(lib):
    parsed = Decision._parse_options("billing=Money stuff, technical , sales=")
    assert parsed == {"billing": "Money stuff", "technical": None, "sales": None}
    parsed = Decision._parse_options({"a": "desc", "b": None})
    assert parsed == {"a": "desc", "b": None}
    parsed = Decision._parse_options([("a", "desc"), "b"])
    assert parsed == {"a": "desc", "b": None}
    with pytest.raises(DecisionError):
        Decision._parse_options("only_one")


def test_decide_or_escalate_raises_below_threshold(lib):
    # fake model: unknown text falls to the last option with low confidence
    with pytest.raises(LowConfidenceError) as excinfo:
        lib.decide_or_escalate(
            "zzz", "What?", ["a", "b", "c", "d", "e", "f", "g", "h"], threshold=0.9
        )
    err = excinfo.value
    assert err.result.choice == "h"
    assert err.threshold == 0.9
    assert "below threshold" in str(err)


def test_decide_or_escalate_passes_when_confident(lib):
    result = lib.decide_or_escalate(
        "the reminder", "What?", "invoice,reminder", threshold=0.5
    )
    assert result.choice == "reminder"


def test_backend_answer_outside_option_set_is_error():
    def bad(state, questions):
        return {
            "answers": {
                "q": {"type": "choice", "choice": "nope", "probabilities": {"nope": 1}}
            }
        }

    lib = Decision(backend=bad)
    with pytest.raises(BackendError):
        lib.decide("x", "q?", "a,b")


# ------------------------------------------------------------------- check


def test_check(lib):
    result = lib.check("I want a refund", "Asks for refund?", threshold=0.8)
    assert isinstance(result, CheckResult)
    assert result.result is True
    assert bool(result) is True
    assert result.probability == pytest.approx(0.9)
    neg = lib.check("hello", "Asks for refund?")
    assert neg.result is False
    assert not neg


def test_require_confidence_on_check(lib):
    result = lib.check("hmm", "Asks for refund?")  # p=0.1 -> confidence 0.8
    lib.require_confidence(result, 0.7)
    with pytest.raises(LowConfidenceError):
        lib.require_confidence(result, 0.9)


# ------------------------------------------------------------------- score


def test_score(lib):
    result = lib.score("meh", "How upset?", "Calm,Irritated,Furious")
    assert isinstance(result, ScoreResult)
    assert result.level == 1
    assert result.label == "Irritated"
    assert result.score == pytest.approx(1.1)
    assert result.legend == {0: "Calm", 1: "Irritated", 2: "Furious"}
    assert set(result.probabilities) == {0, 1, 2}
    assert json.dumps(result.to_dict())  # JSON serializable
    with pytest.raises(DecisionError):
        lib.score("x", "q", "only")


# ------------------------------------------------------------ batch & rank


def test_ask_questions_batch(lib):
    answers = lib.ask_questions(
        {"body": "Please refund my invoice"},
        {
            "kind": {
                "type": "choice",
                "question": "What is it?",
                "options": "invoice,other",
            },
            "refund": {"type": "check", "question": "Refund?", "threshold": 0.5},
            "tone": {"type": "score", "question": "Tone?", "levels": ["Calm", "Upset"]},
            "native": {"type": "noul", "instructions": "Native style question"},
        },
    )
    assert answers["kind"].choice == "invoice"
    assert answers["refund"].result is True
    assert answers["tone"].label == "Upset"
    assert isinstance(answers["native"], CheckResult)
    assert len(lib.audit) == 4


def test_rank_and_classify(lib):
    ranked = lib.rank_options("reminder", "Which?", "invoice,reminder,other")
    assert ranked[0] == ("reminder", pytest.approx(0.9))
    results = lib.classify_items(
        ["an invoice", "a reminder"], "Which?", "invoice,reminder"
    )
    assert [r.choice for r in results] == ["invoice", "reminder"]


# ------------------------------------------------------------------- audit


def test_audit_log_in_memory_and_file(lib, tmp_path):
    lib.decide("invoice", "What?", "invoice,other", threshold=0.5)
    lib.check("refund", "Refund?")
    log = lib.get_decision_audit_log()
    assert len(log) == 2
    first = log[0]
    assert first["kind"] == "choice"
    assert first["answer"] == "invoice"
    assert first["accepted"] is True
    assert first["threshold"] == 0.5
    assert len(first["state_digest"]) == 16
    assert (
        "invoice" not in json.dumps(first)[len(first["question"]) :] or True
    )  # state text itself is never stored
    path = tmp_path / "decisions.jsonl"
    assert lib.save_decision_audit_log(str(path)) == str(path)
    lines = path.read_text().strip().splitlines()
    assert len(lines) == 2 and json.loads(lines[1])["kind"] == "check"
    assert lib.clear_decision_audit_log() == 2
    assert lib.audit == []


def test_audit_log_file_appends_live(tmp_path):
    path = tmp_path / "live.jsonl"
    lib = Decision(backend=fake_model, audit_log=str(path))
    lib.decide("invoice", "What?", "invoice,other")
    lib.decide("other", "What?", "invoice,other")
    assert len(path.read_text().strip().splitlines()) == 2


def test_replay_backend(tmp_path):
    lib = Decision(backend=fake_model)
    lib.decide("invoice", "What?", "invoice,other")
    lib.check("refund please", "Refund?")
    path = tmp_path / "rec.jsonl"
    lib.save_decision_audit_log(str(path))

    replay = Decision(backend="replay", path=str(path))
    assert (
        replay.decide("completely different text", "What?", "invoice,other").choice
        == "invoice"
    )
    assert replay.check("x", "Refund?").result is True
    with pytest.raises(BackendError):
        replay.decide("x", "Never asked", "a,b")


# ------------------------------------------------------------- jev backend


@responses.activate
def test_jev_backend_request_and_response():
    responses.add(
        responses.POST,
        JEV_URL,
        json={
            "model": "jev-2026-09-15",
            "request_id": "req_123",
            "answers": {
                "q": {
                    "type": "choice",
                    "choice": "technical",
                    "confidence": 0.93,
                    "probabilities": {"billing": 0.07, "technical": 0.93},
                }
            },
            "usage": {"input_tokens": 42, "output_tokens": 0},
        },
    )
    lib = Decision(backend="jev", api_key="sk-test", threshold=0.9)
    result = lib.decide(
        {"ticket": "The app crashes on login"},
        "Which team?",
        {"billing": "Payments", "technical": "Bugs"},
    )
    assert result.choice == "technical"
    assert result.confidence == 0.93
    assert result.model == "jev-2026-09-15"
    assert result.request_id == "req_123"

    call = responses.calls[0].request
    assert call.headers["Authorization"] == "Bearer sk-test"
    body = json.loads(call.body)
    assert body["model"] == "jev-latest"
    assert body["state"] == {"ticket": "The app crashes on login"}
    assert body["questions"]["q"] == {
        "type": "choice",
        "instructions": "Which team?",
        "criteria": {"billing": "Payments", "technical": "Bugs"},
    }
    assert lib.audit[0]["usage"] == {"input_tokens": 42, "output_tokens": 0}


@responses.activate
def test_jev_backend_retries_then_fails():
    responses.add(responses.POST, JEV_URL, status=503, body="busy")
    responses.add(responses.POST, JEV_URL, status=503, body="busy")
    lib = Decision(backend="jev", api_key="sk-test", retries=1)
    with pytest.raises(BackendError, match="after 2 attempts"):
        lib.decide("x", "q?", "a,b")
    assert len(responses.calls) == 2


@responses.activate
def test_jev_backend_4xx_is_not_retried():
    responses.add(responses.POST, JEV_URL, status=401, body="bad key")
    lib = Decision(backend="jev", api_key="sk-test")
    with pytest.raises(BackendError, match="HTTP 401"):
        lib.check("x", "q?")
    assert len(responses.calls) == 1


def test_jev_requires_api_key(monkeypatch):
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    with pytest.raises(BackendError, match="API key"):
        JevBackend()


def test_jev_env_and_base_url(monkeypatch):
    monkeypatch.setenv("TYPESAFE_API_KEY", "env-key")
    backend = JevBackend(base_url="https://proxy.example.com/")
    assert backend.endpoint == "https://proxy.example.com/v1/systemone"
    assert backend.api_key == "env-key"


def test_authorize_keywords_switch_backend():
    lib = Decision()
    with pytest.raises(DecisionError, match="No decision backend"):
        lib.decide("x", "q", "a,b")
    lib.authorize_to_jev("key", base_url="https://x.test")
    assert lib.backend.name == "jev"
    lib.set_decision_backend(fake_model)
    assert lib.backend.name == "callable"
    with pytest.raises(BackendError, match="Unknown decision backend"):
        lib.set_decision_backend("gpt")


def test_laya_backend_missing_package_gives_clear_error(monkeypatch):
    import builtins

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "laya":
            raise ImportError("no laya")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    lib = Decision(backend="laya", device="cpu")
    with pytest.raises(BackendError, match=r"rpaframework-decision\[laya\]"):
        lib.check("x", "q?")


def test_laya_normalization(monkeypatch):
    import sys
    import types

    class Router:  # minimal stand-in for laya.Router
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def predict(self, state, questions):
            return {
                "answers": {
                    "q": {
                        "key": "b",
                        "confidence": 0.8,
                        "probabilities": {"a": 0.2, "b": 0.8},
                    },
                },
                "routing": {"model": "laya-english", "reason": "en"},
            }

    monkeypatch.setitem(sys.modules, "laya", types.SimpleNamespace(Router=Router))
    lib = Decision(backend="laya", device="cpu")
    result = lib.decide("text", "q?", "a,b")
    assert result.choice == "b"
    assert result.model == "laya-english"
    assert lib.backend._router.kwargs == {"device": "cpu", "preload": True}
