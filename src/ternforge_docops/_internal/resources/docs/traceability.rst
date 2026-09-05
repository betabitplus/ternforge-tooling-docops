:orphan:

Engineering traceability
========================

The Sphinx-Needs graph is the engineering source of truth. Engineering Experiments
preserve durable learning from uncertain investigations, Requirements define
obligations, Architecture Decisions preserve significant rationale, and verification
and implementation evidence link into the same graph.

Requirement hierarchy
---------------------

.. needtable::
   :columns: id;title;type;status;revision;derives;derives_back
   :filter: type in ["goal", "feature", "req", "treq"]

Engineering experiments
-----------------------

Experiments preserve observations that materially informed a later contract or
decision. ``informs`` records provenance; experiments never satisfy implementation
or verification obligations.

.. needtable::
   :columns: id;title;experiment_date;informs
   :filter: type == "exp"

Architecture decisions
----------------------

Architecture decisions preserve significant rationale without becoming verification
obligations. ``affects`` connects a decision to what it shapes and ``supersedes``
preserves replacement history.

.. needtable::
   :columns: id;title;status;decision_date;informs_back;affects;supersedes;supersedes_back
   :filter: type == "adr"

Implementation evidence
-----------------------

Implementation evidence is represented by ``IMPL_*`` needs linked to the exact
requirement revision they implement. Language adapters may attach source URLs, but
the graph relationship remains language-agnostic.

.. needtable::
   :columns: id;title;implements;source_url
   :filter: type == "impl"

Verification evidence
---------------------

Test evidence links to an exact requirement revision and declares its verification
kind. Only a passing testcase satisfies a requested verification obligation; skipped,
expected-failure, failed, and errored executions remain visible evidence.

Requirement evidence coverage:

.. needtable::
   :columns: id;title;status;revision;required_evidence;implements_back;verifies_back
   :filter: type in ["req", "treq"]

Non-passing verification evidence (empty on a healthy build):

.. needtable::
   :columns: id;title;result;verification_kind;verifies
   :filter: type == "testcase" and result != "passed"

Graph inventory
---------------

.. needtable::
   :columns: id;title;type;required_evidence
   :filter: type in ["goal", "feature", "req", "treq", "exp", "adr", "impl", "testcase"]
