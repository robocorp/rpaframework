rpaframework-decision
=====================

Typed, calibrated decisions for `RPA Framework`_ robots, made by a
**decision model** (a *System One* model) such as `Jev`_ or the open-weight
`Laya`_, instead of a generative LLM.

A decision model does not write text. You give it a *state* (the thing to
look at) and a question with a closed set of answers, and it returns one of
those answers plus a probability. That makes it fast (tens to hundreds of
milliseconds), cheap, and easy to branch on from Robot Framework or Python.

Why in an RPA stack
-------------------

Most of the branch points in a bot are closed questions:

- routing work items (``invoice`` / ``credit note`` / ``reminder`` / ``junk``)
- classifying failures (business exception vs. application exception)
- guardrails before a side effect (*is it safe to auto-reply to this email?*)
- deciding when to hand off to a human, with the confidence as the gate

``RPA.Decision`` turns each of these into one keyword, records every call in
an audit log, and keeps the backend swappable: hosted Jev today, local Laya
when data must not leave the machine, a replayed log in CI.

Install
-------

.. code-block:: bash

    pip install rpaframework-decision          # hosted backends (Jev)
    pip install rpaframework-decision[laya]    # + local open-weight Laya

Robot Framework
---------------

.. code-block:: robotframework

    *** Settings ***
    Library    RPA.Robocorp.Vault
    Library    RPA.Decision    threshold=0.85    audit_log=output/decisions.jsonl

    *** Tasks ***
    Route a document
        ${secrets}=    Get Secret    TypeSafe
        Authorize To Jev    api_key=${secrets}[api_key]

        ${result}=    Decide    ${document_text}
        ...    question=What kind of document is this?
        ...    options=invoice=A request for payment,credit_note=A credit against an invoice,other
        Log    ${result.choice} with confidence ${result.confidence}

        ${safe}=    Check    ${email_body}
        ...    question=Is this a routine request that a template answers fully?
        ...    threshold=0.9
        IF    ${safe}    Send Template Reply

        TRY
            ${team}=    Decide Or Escalate    ${ticket}
            ...    question=Which team owns this ticket?
            ...    options=billing,technical,sales
        EXCEPT    LowConfidenceError*    type=glob
            Escalate To Human    ${ticket}
        END

Python
------

.. code-block:: python

    from RPA.Decision import Decision, LowConfidenceError

    decide = Decision(backend="jev", api_key="...", threshold=0.85)
    result = decide.decide(text, "What kind of document is this?", ["invoice", "other"])
    print(result.choice, result.confidence, result.probabilities)

    local = Decision(backend="laya", device="cpu")   # nothing leaves the machine
    if local.check(email, "Does the sender ask for a refund?"):
        ...

Keywords
--------

==========================  =====================================================
``Decide``                  Pick one option; returns choice, confidence, probabilities
``Decide Or Escalate``      Same, but fails with ``LowConfidenceError`` below threshold
``Check``                   Yes/no with a calibrated probability
``Score``                   Position on an ordered rubric (2 - 10 levels)
``Rank Options``            All options ordered by probability
``Ask Questions``           Several questions about one state in a single call
``Classify Items``          ``Decide`` over a list of states
``Require Confidence``      Fail unless a result meets a threshold
``Authorize To Jev``        Use TypeSafe's hosted model
``Use Laya``                Use the open-weight model locally
``Set Decision Backend``    Any backend, incl. ``replay`` and Python callables
``Get/Save/Clear Decision Audit Log``  Inspect or persist what was decided and why
==========================  =====================================================

What a decision model is not good at
------------------------------------

Decision models are strong on recognition and weak on arithmetic and
multi-step reasoning. Compute totals in Python; ask the model whether a
document *is* an invoice, not whether its total is correct. Measure accuracy
on your own data from the audit log before trusting a threshold.

.. _RPA Framework: https://rpaframework.org
.. _Jev: https://typesafe.ai
.. _Laya: https://github.com/NandhaKishorM/laya
