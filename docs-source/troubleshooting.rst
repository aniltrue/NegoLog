Troubleshooting
===============

Start with the symptom below. Keep the terminal open while using the web
interface: it contains Python errors that a result workbook cannot fully explain.
These instructions assume you are in the NegoLog repository root.

Installation and imports
------------------------

``python3.10`` or ``py -3.10`` is not found
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Install Python 3.10 for your operating system, then create the environment as
shown in :doc:`getting-started`. An existing ``python`` command may point to a
different version. The pinned dependency ranges target Python 3.10; substituting
a newer interpreter can cause incompatible-wheel or package-build errors.

``ModuleNotFoundError`` for ``nenv``, ``numpy``, or another dependency
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Check the working directory and interpreter:

.. code-block:: console

   python -c "from pathlib import Path; import sys; print(Path.cwd()); print(sys.executable)"
   python -m pip check

The working directory should contain ``run.py``, ``requirements.txt``, and
``nenv/``. Activate the repository environment and install with
``python -m pip install -r requirements.txt``. Use the same ``python`` to install
dependencies and run the program. Do not create local files named ``nenv.py``,
``numpy.py``, ``pandas.py``, or ``yaml.py`` that shadow imports.

PowerShell refuses to run ``Activate.ps1``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Activation is optional. Use ``.\.venv\Scripts\python.exe`` instead of
``python`` for installation and execution; the Windows quickstart includes the
exact commands. There is no need to change the system execution policy.

``quickstart.yaml`` is missing
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

These guides accompany the maintenance preview branch, not an older checkout.
Check ``git branch --show-current`` and ``git rev-parse HEAD``, then follow
:doc:`getting-started` to obtain the matching revision. Preserve an existing
experiment's checkout instead of replacing it merely to run this example.

Configuration and output
------------------------

Unknown field, invalid component, or import-path error
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Start from the complete configuration in :doc:`tutorials`. Use YAML spaces
instead of tabs and exact class names from :doc:`components`.
``ConcederAgent`` is a class name; ``Conceder`` is its display name.
Custom paths look like ``my_agent.MyConceder``; keep ``my_agent.py`` in the
repository root or another importable Python package. A selected component must
be a concrete subclass of the relevant NegoLog interface.

Round limits must be positive integers, at least one deadline must be set,
and a one-agent tournament needs ``self_negotiation: true``. Quote domain IDs,
especially identifiers with leading zeros. Use ``null`` for an unused deadline.

Domain not found or missing catalog entry
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``domains: ["0"]`` needs ``domains/domain0/profileA.json``,
``domains/domain0/profileB.json``, and its metadata row in
``domains/domains.xlsx``. Run from the repository root. For new domains, the
web interface manages creation and catalog registration together. Calling a
Python domain generator directly returns metadata but does not register it in
the catalog. See :doc:`runs` before adding generated profiles to a tournament.

Output path rejected, or old results disappeared
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Use a dedicated directory such as ``results/my-experiment-01``. A tournament
replaces that directory's contents; assign another path for each run you want
to retain. Source/input folders, symlink targets, files, and ancestor directories
are rejected as result destinations. Close workbooks before running on Windows
to avoid file-lock errors. Preflight checks do not replace a backup policy.

``NashDistance`` or ``KalaiDistance`` is missing
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``TournamentSummaryLogger`` consumes columns produced by ``BidSpaceLogger``.
Include both in ``loggers``, as in the quickstart. To start with a known working
set of dependencies, copy the bundled quickstart rather than selecting every
logger at once. :doc:`components` explains logger combinations.

No agreement, or an ``Error`` / ``TimedOut`` result
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A session with ``Result: Failed`` reached its negotiation deadline without an
agreement; it is a valid negotiation outcome. ``Error`` indicates a component
execution error, and ``TimedOut`` indicates an agent callback exceeded its
execution limit. Check ``Who`` in ``TournamentResults`` and the terminal's
exception or callback message. A tournament-level web ``Error`` is different
from a session outcome. Retain these cases in reports rather than counting them
as agreements or silently dropping them.

Model correlations are blank or ``NaN``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Rank correlation is undefined for a constant utility vector, including some
initial uniform estimates. Optional MAPE is undefined by default when a true
utility equals zero. Excel may display these values as blank cells. They do not
mean zero error, perfect accuracy, or a missing model update. Keep missingness
explicit; see :doc:`models` and :doc:`logging` before aggregating scores.

A run is unexpectedly slow
~~~~~~~~~~~~~~~~~~~~~~~~~~

First reproduce with domain ``0`` and the quickstart's two agents. Total work
depends on ordered pairings, repeats, bid-space size, and selected loggers.
``EstimatorMetricLogger`` evaluates estimates at every offer by default. Try
``EstimatorOnlyFinalMetricLogger`` or explicit sampling if your question permits
it. A round deadline limits negotiation rounds, not the cost of bid enumeration
or end-of-tournament analysis. Random domain generation bounds candidate
attempts but can still be expensive on very large candidate domains.

Local web interface
-------------------

Port 5000 is in use
~~~~~~~~~~~~~~~~~~~

Choose another local port and open the matching address:

.. code-block:: console

   python app.py -p 5001

Open http://127.0.0.1:5001. Keep using that origin for the interface and its
requests; there is no need to edit JavaScript configuration.

The interface is blank, or local requests are rejected
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Run ``python app.py`` from the repository root and open the HTTP address printed
by Flask. Do not open the HTML file directly, and do not use a remote hostname.
The prebuilt web interface is included, so Node.js is unnecessary. Reload the
page after changing the server port or updating the checkout; check the browser
console and Python terminal if it still fails.

Another tournament is active, or domain editing is unavailable
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The web process permits one active tournament because random streams and
plotting settings are shared. Wait for it to finish before editing domains or
starting another. A cancellation request may need to wait for the current
callback to return; blocking native code cannot always be interrupted immediately.
See :doc:`runs` for run states and cancellation behavior.

Documentation and reporting issues
----------------------------------

The published HTML disagrees with the current code
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The checked-in ``docs/`` HTML is a historical snapshot. Use the current
``docs-source/`` guides and build instructions from this checkout. A Sphinx
``ModuleNotFoundError`` usually means runtime dependencies were omitted from
the documentation environment; install both requirement files before building.

Report a reproducible issue
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Include the command, complete error text, operating system, Python version,
Git commit, minimal YAML, and a small shareable domain when needed. State the
expected behavior and what happened. Remove confidential data and credentials.
Run ``python -m pip check`` and retain its result. The
:download:`contribution guide <../CONTRIBUTING.md>` explains test commands and
the issue-reporting workflow.
