:orphan:

Specification health
====================

This view summarizes the authored Goal → Feature → Requirement hierarchy without
creating a second requirements store. Structure comes from Sphinx-Needs links;
direct evidence means the current requirement revision has every declared
``required_evidence`` kind; deep coverage propagates any active descendant gap upward.
Draft and deprecated contracts are not counted as active evidence obligations.

.. ternforge-specification-health::

For concrete execution details use :doc:`verification`. For dense relationship and
source provenance use :doc:`traceability`.
