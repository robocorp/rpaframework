##########
Python API
##########

********
Decision
********

.. autoclass:: RPA.Decision.Decision
   :members:
   :inherited-members:
   :undoc-members:

Result types
============

.. autoclass:: RPA.Decision.ChoiceResult
   :members:

.. autoclass:: RPA.Decision.CheckResult
   :members:

.. autoclass:: RPA.Decision.ScoreResult
   :members:

.. autoexception:: RPA.Decision.LowConfidenceError

Backends
========

.. automodule:: RPA.Decision.backends
   :members: DecisionBackend, JevBackend, LayaBackend, CallableBackend, ReplayBackend
