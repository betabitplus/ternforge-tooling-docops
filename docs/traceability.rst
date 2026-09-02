Requirements traceability
=========================

Requirements are the engineering source of truth. Verification and implementation
evidence are linked into the same Sphinx-Needs graph.

Requirement hierarchy
---------------------

.. needtable::
   :columns: id;title;type;derives;derives_back
   :filter: type in ["goal", "feature", "req", "treq"]

Implementation evidence
-----------------------

Implementation markers live next to the code they justify::

   # @impl Short implementation title, IMPL_EXAMPLE, [REQ_EXAMPLE[revision==1]]

The marker creates an ``IMPL_*`` need with a source link and an ``implements``
edge to the referenced requirement revision. Requirements that request ``impl``
evidence must have at least one such incoming edge; a requirement revision bump
invalidates stale implementation links until they are reviewed and repinned.

.. src-trace::
   :project: python

Verification evidence
---------------------

Pytest evidence links to an exact requirement revision and declares its evidence
kind. A requested verification kind is satisfied only by a testcase whose result
is ``passed``; skipped and expected-failure results remain visible evidence but do
not satisfy the requirement obligation. Revision bumps invalidate stale
``verifies`` links until the verification has been reviewed and repinned.

Evidence matrices
-----------------

Requirement evidence coverage:

.. needtable::
   :columns: id;title;status;revision;required_evidence;implements_back;verifies_back
   :filter: type in ["req", "treq"]

Non-passing verification evidence (empty on a healthy build):

.. needtable::
   :columns: id;title;result;verification_kind;verifies
   :filter: type == "testcase" and result != "passed"

Execution evidence and agent views
----------------------------------

Required CI publishes one ``python-test-evidence-<sha>`` artifact containing the
pytest JUnit report, the context-enabled ``.coverage`` database,
``coverage.json`` with per-test contexts, and raw ``allure-results``. JUnit is
the authoritative verification input imported into Sphinx-Needs. Coverage
contexts and Allure remain auxiliary execution evidence; they are intentionally
not converted into a second TEST-to-CODE graph or a separately hosted report.

The built documentation already exposes the authoritative graph as
``needs.json`` and provides derived agent-readable page Markdown plus
``llms.txt`` and ``llms-full.txt``. A separate ``ai_docs_index.json`` is
therefore intentionally not generated because it would duplicate those views.

Graph inventory
---------------

.. needtable::
   :columns: id;title;type;required_evidence
   :filter: type in ["goal", "feature", "req", "treq", "adr", "exp", "impl", "testcase"]
