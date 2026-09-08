:orphan:

Verification
============

This page summarizes whether requested verification layers are covered and where concrete
execution evidence can be inspected. Imported JUnit remains the authoritative TEST input in
the Sphinx-Needs graph.

Release outcome
---------------

.. grid:: 2 2 4 4
   :gutter: 2

   .. grid-item-card:: Executed
      :class-card: portal-card

      :need_count:`type == "testcase"` tests

   .. grid-item-card:: Passed
      :class-card: portal-card

      :need_count:`type == "testcase" and result == "passed"` passed

   .. grid-item-card:: Failed / errored
      :class-card: portal-card

      :need_count:`type == "testcase" and (result == "failed" or result == "error")` failed or errored

   .. grid-item-card:: Skipped
      :class-card: portal-card

      :need_count:`type == "testcase" and result == "skipped"` skipped

Verification matrix
-------------------

Rows are product requirements and engineering constraints; columns are verification layers.
``x/x`` means all executions in that layer passed. ``missing`` means the object requests that
verification kind but no execution was found. A dash means the layer is not requested.

.. raw:: html

   <iframe
     class="verification-matrix-frame"
     src="verification-matrix.html"
     title="Requirement verification matrix"
   ></iframe>

Inspect concrete evidence
-------------------------

.. grid:: 1 1 2 2
   :gutter: 3

   .. grid-item-card:: Executable specifications
      :link: specifications
      :link-type: doc
      :class-card: portal-card

      Inspect current BDD behavior as Feature → Rule → Scenario → Given/When/Then with rich
      evidence beside the step that produced it.

   .. grid-item-card:: All test execution
      :link: test-results/index.html
      :link-type: url
      :class-card: portal-card

      Browse the complete current execution inventory across all verification layers in Allure.

For exact requirement, implementation, and verification relationships use :doc:`traceability`.
