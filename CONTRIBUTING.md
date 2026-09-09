# Contributing to NegoLog

You can help by making an example easier to follow, reporting a reproducible
problem, contributing a domain, or improving a component. Start with a small
change that another researcher can run and review.

[Report an issue](https://github.com/aniltrue/NegoLog/issues) ·
[Browse the framework](README.md) · [Component catalog](docs-source/components.rst) ·
[Migration notes](MAINTENANCE.md)

## Choose a contribution

| Contribution | A useful first step | Include in the change |
| --- | --- | --- |
| Documentation or example | Follow the [first-run guide](docs-source/getting-started.rst) and identify the step that was unclear. | A runnable command or example, its expected output, and updated links. |
| Bug report or fix | Reduce the failure to one small domain and the fewest components. | Expected/actual behavior and a regression that fails before the fix. |
| Negotiation domain | Create or edit a domain through the local web interface. | Both profiles, the matching catalog entry, and the domain's source or synthetic construction. |
| Agent or opponent model | Implement the relevant interface in an importable module. | Source attribution, assumptions, a small round-limited example, and focused tests. |
| Logger or analysis | Start from an existing logger with similar callbacks. | Column definitions, behavior for missing/constant data, and one example of the output. |

A custom component can be selected by its full Python path, such as
`my_agents.MyAgent`, without changing the built-in registry. Follow the
[extension tutorial](docs-source/tutorials.rst) to try it locally. For an upstream
contribution, include a registry export and a catalog entry when the component
is intended to be available by its short class name.

## Set up a working copy

Fork the repository on GitHub if you do not have write access, then clone your
fork. From the checkout root, use Python 3.10 and the existing dependency file:

```sh
git switch -c improve-my-component
python3.10 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt "pytest>=9.0.3,<10"
```

On Windows PowerShell, use `py -3.10 -m venv .venv` and
`.\.venv\Scripts\Activate.ps1` for the environment steps. Keep runtime dependency
changes separate from an unrelated correction so they can be assessed on their
own.

## Report a problem others can reproduce

Open an issue with the shortest complete example you can provide. This template
also works for the problem description in a pull request:

```text
What I expected:
What happened instead:

Revision: output of git rev-parse HEAD
Environment: operating system and python --version
Command: exact command, run from the repository root
Configuration: minimal YAML or Python example
Domain: bundled identifier, or small synthetic profiles
Failure: relevant traceback and session/result row
Reproduction: every run, or the seed and frequency observed
```

Include the selected agents, estimators, loggers and deadline. `Error`,
`TimedOut` and a normal deadline without agreement (`Failed`) describe different
outcomes; retain the original label. Remove credentials and unrelated local data
from attachments. Share a small synthetic reproduction when original profiles
cannot be redistributed.

## Validate a change

Run the tests that exercise the changed behavior while developing:

| Area | Focused command |
| --- | --- |
| Agent behavior | `python -m pytest -q tests/test_agent_runtime.py tests/test_degenerate_preferences.py` |
| Opponent models and metrics | `python -m pytest -q tests/test_model_migration.py tests/test_opponent_metrics.py` |
| Logging and workbooks | `python -m pytest -q tests/test_log_reprocessing.py tests/test_excel_log_contracts.py` |
| Domains and the web interface | `python -m pytest -q tests/test_domain_management.py tests/test_web_workflows.py` |
| Tournament configuration and lifecycle | `python -m pytest -q tests/test_tournament_configuration.py tests/test_core_runtime.py` |

Add the component's own regression test when the listed group does not cover
your change. Before submitting a runtime change, run the complete suite:

```sh
python -m pip check
python -m pytest -q tests
```

Use small synthetic profiles for numerical and integration regressions. Cover
the failing input and a normal case that should keep its previous behavior.
Do not silently change random draws, deadline assumptions or experiment results
to make a test pass. Record any intentional public API or policy change in
[MAINTENANCE.md](MAINTENANCE.md).

The test workflow checks Python 3.10 on Linux, Windows and macOS. Local success
does not prove every agent/domain pairing works or establish a performance
advantage. Include the checks actually run and any remaining limitations in the
pull request. For documentation-only edits, build the documentation and run the
examples you changed; a new test that only repeats the prose is unnecessary.

## Preserve the meaning of an experiment

Describe an implementation correction with the input that was wrong and the
expected behavior. Describe a change to concession curves, initialization,
sampling, deadlines or random draws as a behavior change, even when it is in an
existing class. Document public API and output-column changes in
[MAINTENANCE.md](MAINTENANCE.md).

Retain agent/model authors, licenses and source references. A port may differ
from the original paper or implementation: identify those differences rather
than assuming that an inherited name guarantees equivalent results. When a
contribution claims a performance improvement, provide the evaluation setup and
results separately from functional test evidence. Record the revision, profiles,
configuration, seed and resolved environment for an experiment.

## Update documentation

Edit the current [Sphinx sources](docs-source/README.md) and relevant Python
docstrings, then build the HTML in a separate output folder. Review the changed
pages, signatures and links. The older generated files in `docs/` are a
historical snapshot, not the source for the current API. The docs workflow
uploads an artifact for review and does not deploy a public site.

README examples should run from the repository root, use bundled small domains
where possible, and state when an output directory is replaced. Show readers
what to open after the command finishes. Keep installed runtime dependencies
separate from optional documentation tools.

## Open a pull request

Keep one purpose per pull request. Explain these three things so a maintainer
can review it without the issue discussion:

1. **Problem and result:** what input or user action exposed the issue, and what
   happens after the change.
2. **Compatibility:** whether agents, estimators, APIs, random draws, saved
   profiles or output columns change.
3. **Validation:** exact commands run, their results and any limitation still
   relevant to this change.

Before committing, inspect `git status --short` and `git diff --check`. Commit
only the intended source, documentation and small test fixtures. Keep generated
tournament output, local environments, credentials and unrelated data out of
the pull request. Retain the existing [GPLv3 license](LICENSE) and citations for
reused implementations.

Maintainers review, merge and release changes. A passing test suite is useful
review evidence; it does not itself publish a new version. If you use NegoLog
in a paper, the [citation entry](README.md#cite-negolog) identifies the framework;
cite the original agent or model work as well when it is relevant to your study.
