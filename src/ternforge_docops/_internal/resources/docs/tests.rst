:orphan:

Test results
============

Concrete executions are presented from the same retained evidence run. JUnit is the
authoritative verification input for Sphinx-Needs. :doc:`specifications` is the narrative
BDD view; Allure remains the forensic browser for the complete current execution inventory.

Current verification inventory
------------------------------

.. grid:: 1 2 4 4
   :gutter: 2

   .. grid-item-card:: BDD

      :need_count:`type == "testcase" and verification_kind == "bdd"` executable scenarios

   .. grid-item-card:: Unit

      :need_count:`type == "testcase" and verification_kind == "unit"` unit tests

   .. grid-item-card:: Integration

      :need_count:`type == "testcase" and verification_kind == "integration"` integration tests

   .. grid-item-card:: Property

      :need_count:`type == "testcase" and verification_kind == "property"` property tests

Choose a perspective
--------------------

.. grid:: 1 1 2 2
   :gutter: 3

   .. grid-item-card:: Executable specifications
      :link: specifications
      :link-type: doc

      Read Feature → Rule → Scenario → Given/When/Then as current living documentation with
      rich evidence beside the step that produced it.

   .. grid-item-card:: All test execution
      :link: test-results/index.html
      :link-type: url

      Browse the complete current BDD, unit, integration, and property execution inventory in
      the generic Allure forensic view.

For authoritative requirement-to-test relationships use :doc:`verification`.

Forensic execution browser
--------------------------

.. button-link:: test-results/index.html
   :color: primary
   :shadow:

   Open all test results full screen
