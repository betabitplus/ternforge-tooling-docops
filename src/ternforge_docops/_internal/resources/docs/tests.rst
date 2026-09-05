:orphan:

Test results
============

Concrete executions are presented in several views generated from the same evidence
run. JUnit is the authoritative verification input for Sphinx-Needs; Allure is the
human-facing execution presentation.

Current verification inventory
------------------------------

.. grid:: 1 2 4 4
   :gutter: 2

   .. grid-item-card:: BDD
      :class-card: portal-card

      :need_count:`type == "testcase" and verification_kind == "bdd"` executable scenarios

   .. grid-item-card:: Unit
      :class-card: portal-card

      :need_count:`type == "testcase" and verification_kind == "unit"` unit tests

   .. grid-item-card:: Integration
      :class-card: portal-card

      :need_count:`type == "testcase" and verification_kind == "integration"` integration tests

   .. grid-item-card:: Property
      :class-card: portal-card

      :need_count:`type == "testcase" and verification_kind == "property"` property tests

Choose a perspective
--------------------

.. grid:: 1 1 3 3
   :gutter: 3

   .. grid-item-card:: BDD stories
      :link: test-results/bdd/index.html
      :link-type: url
      :class-card: portal-card

      Read Feature → Rule → Scenario executions as a narrative with rich step evidence.

   .. grid-item-card:: Verification by requirement
      :link: test-results/requirements/index.html
      :link-type: url
      :class-card: portal-card

      Start from a requirement, then inspect its BDD, unit, integration, or property
      executions.

   .. grid-item-card:: All tests by layer
      :link: test-results/all/index.html
      :link-type: url
      :class-card: portal-card

      Browse the complete execution inventory grouped by verification layer.

Requirement-centric test evidence
---------------------------------

.. button-link:: test-results/requirements/index.html
   :color: primary
   :shadow:

   Open verification by requirement full screen

.. raw:: html

   <iframe
     class="test-portal-frame"
     src="test-results/requirements/index.html"
     title="Verification by requirement"
   ></iframe>

For authoritative requirement-to-test relationships use :doc:`verification`.
