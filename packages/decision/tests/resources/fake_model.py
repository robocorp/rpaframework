"""Offline stand-in for a decision model, used by the Robot Framework tests.

Exposed as the ``${FAKE_MODEL}`` variable (a callable instance: Robot ignores
plain functions in variable files)."""

import json


def _fake_model(state, questions):
    text = (state if isinstance(state, str) else json.dumps(state)).lower()
    answers = {}
    for qid, q in questions.items():
        if q["type"] == "choice":
            labels = list(q["criteria"])
            hit = next((label for label in labels if label in text), labels[-1])
            probs = {label: 0.05 for label in labels}
            probs[hit] = 1 - 0.05 * (len(labels) - 1)
            answers[qid] = {
                "type": "choice",
                "choice": hit,
                "confidence": probs[hit],
                "probabilities": probs,
            }
        elif q["type"] == "noul":
            answers[qid] = {"type": "noul", "noul": 0.9 if "refund" in text else 0.1}
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


class _CallableModel:
    def __call__(self, state, questions):
        return _fake_model(state, questions)


FAKE_MODEL = _CallableModel()
