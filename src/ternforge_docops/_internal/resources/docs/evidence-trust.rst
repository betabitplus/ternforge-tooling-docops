:orphan:

Evidence trust
==============

This is the evidence-of-evidence route:

TEST → evidence producer → trust basis → calibration / independent verification.

The same Sphinx-Needs graph remains authoritative. Producer records explain what
created or interpreted evidence, how much false confidence a defect could create,
why the producer is trusted, whether a substitute has calibration against external
reality, and what residual doubt remains.

Generic producer registry
-------------------------

The records below are package-owned graph nodes. Consumers add only product-specific
producers and calibration evidence.

.. qualification:: pytest upstream contract
   :id: QUAL_PYTEST_UPSTREAM
   :hide:
   :qualification_kind: upstream-trust
   :target_version: runtime lock
   :evidence_url: https://docs.pytest.org/en/stable/

.. qualification:: pytest-bdd upstream contract
   :id: QUAL_PYTEST_BDD_UPSTREAM
   :hide:
   :qualification_kind: upstream-trust
   :target_version: runtime lock
   :evidence_url: https://pytest-bdd.readthedocs.io/en/stable/

.. qualification:: Hypothesis upstream contract
   :id: QUAL_HYPOTHESIS_UPSTREAM
   :hide:
   :qualification_kind: upstream-trust
   :target_version: runtime lock
   :evidence_url: https://hypothesis.readthedocs.io/en/latest/

.. qualification:: Allure pytest upstream contract
   :id: QUAL_ALLURE_UPSTREAM
   :hide:
   :qualification_kind: upstream-trust
   :target_version: runtime lock
   :evidence_url: https://allurereport.org/docs/pytest/

.. qualification:: VCR.py upstream contract
   :id: QUAL_VCR_UPSTREAM
   :hide:
   :qualification_kind: upstream-trust
   :target_version: runtime lock
   :evidence_url: https://vcrpy.readthedocs.io/en/latest/

.. qualification:: py-testkit evidence API contract
   :id: QUAL_PY_TESTKIT_EVIDENCE_API
   :hide:
   :qualification_kind: unit-contract
   :target_version: current owner revision
   :evidence_url: https://github.com/betabitplus/ternforge-tooling-py-testkit/blob/main/tests/py_lib_testkit/unit/test_evidence.py

.. qualification:: py-testkit traceability transport contract
   :id: QUAL_PY_TESTKIT_TRACEABILITY
   :hide:
   :qualification_kind: integration-contract
   :target_version: current owner revision
   :evidence_url: https://github.com/betabitplus/ternforge-tooling-py-testkit/blob/main/tests/py_lib_testkit/unit/test_pytest_traceability_plugin.py

.. qualification:: Scripted HTTP socket behavior
   :id: QUAL_SCRIPTED_HTTP_SOCKET
   :hide:
   :qualification_kind: integration-contract
   :target_version: current owner revision
   :evidence_url: https://github.com/betabitplus/ternforge-tooling-py-testkit/blob/main/tests/py_lib_testkit/unit/test_scripted_http_server.py

.. qualification:: Scripted HTTP public support contract
   :id: QUAL_SCRIPTED_HTTP_PUBLIC
   :hide:
   :qualification_kind: unit-contract
   :target_version: current owner revision
   :evidence_url: https://github.com/betabitplus/ternforge-tooling-py-testkit/blob/main/tests/py_lib_testkit/unit/test_public_package.py

.. qualification:: DocOps JUnit materialization contract
   :id: QUAL_JUNIT_IMPORTER_BUILD
   :hide:
   :qualification_kind: integration-contract
   :target_version: current owner revision
   :evidence_url: https://github.com/betabitplus/ternforge-tooling-docops/blob/main/tests/ternforge_docops/test_documentation_build.py

.. qualification:: DocOps JUnit graph contract
   :id: QUAL_JUNIT_IMPORTER_GRAPH
   :hide:
   :qualification_kind: cross-check
   :target_version: current owner revision
   :evidence_url: https://github.com/betabitplus/ternforge-tooling-docops/blob/main/tests/ternforge_docops/test_sphinx_extension.py

.. qualification:: Revision-current evidence health contract
   :id: QUAL_REVISION_HEALTH
   :hide:
   :qualification_kind: unit-contract
   :target_version: current owner revision
   :evidence_url: https://github.com/betabitplus/ternforge-tooling-docops/blob/main/tests/ternforge_docops/test_specification_health.py

.. qualification:: Revision pin graph cross-check
   :id: QUAL_REVISION_GRAPH
   :hide:
   :qualification_kind: cross-check
   :target_version: current owner revision
   :evidence_url: https://github.com/betabitplus/ternforge-tooling-docops/blob/main/tests/ternforge_docops/test_sphinx_extension.py

.. qualification:: Verification narrative projection contract
   :id: QUAL_VERIFICATION_NARRATIVE
   :hide:
   :qualification_kind: unit-contract
   :target_version: current owner revision
   :evidence_url: https://github.com/betabitplus/ternforge-tooling-docops/blob/main/tests/ternforge_docops/test_verification_narrative.py

.. qualification:: Living Specifications projection contract
   :id: QUAL_LIVING_SPECS
   :hide:
   :qualification_kind: unit-contract
   :target_version: current owner revision
   :evidence_url: https://github.com/betabitplus/ternforge-tooling-docops/blob/main/tests/ternforge_docops/test_living_specifications.py

.. producer:: pytest execution engine
   :id: PRODUCER_PYTEST
   :hide:
   :producer_role: upstream-tool
   :producer_version: runtime lock
   :producer_impact: medium
   :producer_purpose: Execute tests and expose collection/result lifecycle facts.
   :risk_if_wrong: Execution status or identity can be misreported.
   :residual_doubt: Project-specific plugins can still change semantics.
   :qualified_by: QUAL_PYTEST_UPSTREAM

.. producer:: pytest-bdd execution layer
   :id: PRODUCER_PYTEST_BDD
   :hide:
   :producer_role: upstream-tool
   :producer_version: runtime lock
   :producer_impact: medium
   :producer_purpose: Bind Gherkin scenarios to pytest execution.
   :risk_if_wrong: Executed behavior can diverge from authored scenarios.
   :residual_doubt: Step implementations remain consumer-owned.
   :qualified_by: QUAL_PYTEST_BDD_UPSTREAM

.. producer:: Hypothesis generator
   :id: PRODUCER_HYPOTHESIS
   :hide:
   :producer_role: upstream-tool
   :producer_version: runtime lock
   :producer_impact: medium
   :producer_purpose: Generate and shrink property-test inputs.
   :risk_if_wrong: Property evidence can overstate explored input behavior.
   :residual_doubt: Strategies and invariants remain product-owned.
   :qualified_by: QUAL_HYPOTHESIS_UPSTREAM

.. producer:: Allure pytest capture
   :id: PRODUCER_ALLURE
   :hide:
   :producer_role: capture-pipeline
   :producer_version: runtime lock
   :producer_impact: medium
   :producer_purpose: Retain execution attachments and structured test metadata.
   :risk_if_wrong: Runtime observations can be dropped or attached to the wrong result.
   :residual_doubt: It preserves producer facts but does not validate their meaning.
   :qualified_by: QUAL_ALLURE_UPSTREAM

.. producer:: VCR.py replay capture
   :id: PRODUCER_VCR
   :hide:
   :producer_role: test-substitute
   :producer_version: runtime lock
   :producer_impact: medium
   :producer_purpose: Replay previously captured HTTP interactions deterministically.
   :risk_if_wrong: Replay evidence can diverge from current external behavior.
   :residual_doubt: Replays are not current live-provider observations.
   :qualified_by: QUAL_VCR_UPSTREAM

.. producer:: Ternforge py-testkit evidence transport
   :id: PRODUCER_PY_TESTKIT
   :hide:
   :producer_role: capture-pipeline
   :producer_version: runtime lock
   :producer_impact: high
   :producer_purpose: Publish normalized runtime observations and producer identities.
   :risk_if_wrong: Downstream assurance can associate incorrect facts with a test.
   :residual_doubt: Product instrumentation must still publish truthful raw facts.
   :qualified_by: QUAL_PY_TESTKIT_EVIDENCE_API;QUAL_PY_TESTKIT_TRACEABILITY

.. producer:: Scripted HTTP server
   :id: PRODUCER_SCRIPTED_HTTP_SERVER
   :hide:
   :producer_role: test-substitute
   :producer_version: py-testkit runtime lock
   :producer_impact: high
   :producer_purpose: Provide deterministic provider-shaped local HTTP interactions.
   :risk_if_wrong: Integration tests can claim protocol behavior the real provider lacks.
   :residual_doubt: Fidelity to a live provider requires separate product calibration.
   :qualified_by: QUAL_SCRIPTED_HTTP_SOCKET;QUAL_SCRIPTED_HTTP_PUBLIC

.. producer:: DocOps JUnit importer
   :id: PRODUCER_JUNIT_IMPORTER
   :hide:
   :producer_role: evidence-transformer
   :producer_version: DocOps runtime release
   :producer_impact: high
   :producer_purpose: Import exact release testcases into the authoritative Needs graph.
   :risk_if_wrong: Tests can be omitted, duplicated, or linked to the wrong claim.
   :residual_doubt: Upstream JUnit fields are trusted as captured execution facts.
   :qualified_by: QUAL_JUNIT_IMPORTER_BUILD;QUAL_JUNIT_IMPORTER_GRAPH

.. producer:: DocOps revision resolver
   :id: PRODUCER_REVISION_RESOLVER
   :hide:
   :producer_role: evidence-transformer
   :producer_version: DocOps runtime release
   :producer_impact: high
   :producer_purpose: Accept proof only when revision-pinned edges match current contracts.
   :risk_if_wrong: Stale evidence can be presented as current proof.
   :residual_doubt: Authored requirement revisions remain a governance responsibility.
   :qualified_by: QUAL_REVISION_HEALTH;QUAL_REVISION_GRAPH

.. producer:: Verification narrative projection
   :id: PRODUCER_VERIFICATION_NARRATIVE
   :hide:
   :producer_role: presentation
   :producer_version: DocOps runtime release
   :producer_impact: medium
   :producer_purpose: Render non-BDD runtime evidence without becoming a second truth store.
   :risk_if_wrong: A reader can misunderstand otherwise valid graph evidence.
   :residual_doubt: Presentation cannot strengthen missing runtime observations.
   :qualified_by: QUAL_VERIFICATION_NARRATIVE

.. producer:: Living Specifications projection
   :id: PRODUCER_LIVING_SPECS
   :hide:
   :producer_role: presentation
   :producer_version: DocOps runtime release
   :producer_impact: medium
   :producer_purpose: Render executed BDD evidence and contract provenance for review.
   :risk_if_wrong: Scenario evidence can be presented under the wrong human context.
   :residual_doubt: Presentation cannot establish external reality beyond captured facts.
   :qualified_by: QUAL_LIVING_SPECS

Producer trust and calibration
------------------------------

.. ternforge-evidence-trust::

Return to verification-assurance for claim-centric layered proof.
