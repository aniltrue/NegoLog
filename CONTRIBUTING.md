# Contributing to NegoLog

Use Python 3.10 and the repository's `requirements.txt`. Keep changes focused on
one behavior and describe the input that exposes a problem, the resulting change,
and its validation. Preserve agent/model source attributions and distinguish
implementation corrections from strategy tuning or measured performance claims.

## Validate a change

```sh
python -m pip install -r requirements.txt "pytest>=8.4,<9"
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
pull request.

## Update documentation

Edit the current [Sphinx sources](docs-source/README.md) and relevant Python
docstrings, then build the HTML in a separate output folder. Review the changed
pages, signatures and links. The older generated files in `docs/` are a
historical snapshot, not the source for the current API. The docs workflow
uploads an artifact for review and does not deploy a public site.

README examples should run from the repository root, use bundled small domains
where possible, and state when an output directory is replaced. Keep installed
runtime dependencies separate from optional documentation tools.

## Review and release

Open a focused pull request with a clear behavior summary and validation.
Maintainer review controls merge and release decisions. Keep generated results,
local environments, credentials and unrelated data out of commits. Retain the
existing [GPLv3 license](LICENSE) and citations for reused implementations.
