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

      :need_count:`type == "testcase"` tests

   .. grid-item-card:: Passed

      :need_count:`type == "testcase" and result == "passed"` passed

   .. grid-item-card:: Failed / errored

      :need_count:`type == "testcase" and (result == "failed" or result == "error")` failed or errored

   .. grid-item-card:: Skipped

      :need_count:`type == "testcase" and result == "skipped"` skipped

Verification matrix
-------------------

Rows are Requirements and Technical requirements; columns are verification layers.
``x/x`` means all executions in that layer passed. ``missing`` means the object requests that
verification kind but no execution was found. A dash means the layer is not requested.

.. ternforge-verification-matrix::

Inspect concrete evidence
-------------------------

.. grid:: 1 1 2 2
   :gutter: 3

   .. grid-item-card:: Executable specifications
      :link: specifications
      :link-type: doc

      Inspect current BDD behavior as Feature → Rule → Scenario → Given/When/Then with rich
      evidence beside the step that produced it.

   .. grid-item-card:: All test execution
      :link: test-results/index.html
      :link-type: url

      Browse the complete current execution inventory across all verification layers in Allure.

For exact requirement, implementation, and verification relationships use :doc:`traceability`.
