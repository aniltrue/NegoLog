NegoLog V2: build, observe, and assess negotiations
===================================================

NegoLog is a Python framework for bilateral automated negotiation. Two agents
exchange offers over a shared domain, each using its own preference profile.
Run existing agents or develop your own, inspect individual negotiations, and
assess opponent models through Excel workbooks and plots.

.. image:: _static/workflow.svg
   :alt: A configured tournament runs two agents on a domain; opponent models observe offers and loggers produce outcomes and assessment results.
   :width: 100%

Choose your starting point
--------------------------

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - I want to...
     - Start here
   * - Run my first negotiation
     - :doc:`getting-started`: installation, two-session example, results, and
       the local browser interface.
   * - Compare existing components
     - :doc:`components`: available agents, estimators, and useful logger choices.
   * - Add my own component
     - :doc:`tutorials`: complete YAML and small importable Python extensions.
   * - Understand model scores
     - :doc:`models` and :doc:`logging`: what is measured, undefined values,
       and assessment cost.
   * - Resolve a problem
     - :doc:`troubleshooting`: installation, configuration, output, and web issues.
   * - Look up a Python interface
     - :doc:`api`: classes and signatures from this checkout.

These pages describe NegoLog V2 (2.1.0). :doc:`getting-started` identifies the
matching repository. When updating an existing
experiment, use the :download:`migration guide <../MAINTENANCE.md>`; the older
checked-in ``docs/`` HTML is a historical snapshot. Agent performance and model
accuracy answer different questions, and the examples are functional
illustrations rather than benchmark rankings.

Guides and reference
--------------------

.. toctree::
   :maxdepth: 2

   getting-started
   tutorials
   components
   cbom
   runs
   models
   logging
   troubleshooting
   api

Cite and contribute
-------------------

If you use NegoLog in research, cite the
`IJCAI 2024 Demo Track paper <https://www.ijcai.org/proceedings/2024/998>`_
and record the code revision used for your experiment. Download
:download:`BibTeX <../CITATION.bib>` or the :download:`repository README <../README.md>`
for citation details. The :download:`contribution guide <../CONTRIBUTING.md>`
explains how to report a reproducible issue or propose a change.

Indices
-------

* :ref:`genindex`
* :ref:`search`
