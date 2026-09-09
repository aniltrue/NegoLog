# Build the current documentation

These sources describe the current public checkout. API signatures and selected
docstrings come from `nenv` through Sphinx autodoc. The checked-in HTML under
[`docs/`](../docs/) is a historical snapshot; it does not describe every current
model or API change.

Use Python 3.10 in a separate environment, from the repository root:

```sh
python3.10 -m venv ../negolog-docs-env
source ../negolog-docs-env/bin/activate
python -m pip install -r requirements.txt -r docs-source/requirements.txt
python -m sphinx -W --keep-going -b html docs-source ../negolog-docs-html
```

On Windows, create the environment with `py -3.10 -m venv ../negolog-docs-env`
and activate `..\negolog-docs-env\Scripts\Activate.ps1`. Then use the same
`python -m pip` and `python -m sphinx` commands.

Open `../negolog-docs-html/index.html`. Build output stays outside the checkout;
do not overwrite the historical HTML as part of a source-only change. The
[documentation workflow](../.github/workflows/docs.yml) builds an HTML artifact
for review. It does not deploy a website or publish a release.

Autodoc imports library modules, so their runtime dependencies must be installed.
The build does not run tournaments, train agents, or call external services.
The Sphinx version is pinned here; the runtime dependency constraints remain in
the existing `requirements.txt`. Record the resolved environment for an exact
historical rebuild; dependency constraints alone are not a complete lockfile.

The earlier RST exports remain in `docs/_sources/`. These focused sources retain
the public library's documentation approach while adding the current models,
preference migration and logging contracts. Edit these sources or the relevant
Python docstrings, then rebuild and inspect the changed pages.
