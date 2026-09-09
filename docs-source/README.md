# NegoLog user guides and API documentation

Choose a guide before building anything:

| Your next step | Guide |
| --- | --- |
| Install and run your first tournament | [Getting started](getting-started.rst) |
| Understand workbooks and use the browser interface | [Read the results and run the UI](getting-started.rst#read-the-results) |
| Configure a study or register a custom agent/logger | [Hands-on tutorials](tutorials.rst) |
| Choose an agent, model, or analysis | [Built-in components](components.rst) |
| Understand domains and run status | [Run lifecycle](runs.rst) |
| Interpret estimation metrics and sampling | [Models](models.rst) and [logging](logging.rst) |
| Resolve an installation or runtime problem | [Troubleshooting](troubleshooting.rst) |
| Look up Python classes | [API reference](api.rst) |

These sources describe the current checkout, including the maintenance preview
in [PR #2](https://github.com/aniltrue/NegoLog/pull/2). Follow the matching branch
instructions in [Getting started](getting-started.rst). API signatures and
selected docstrings are generated from `nenv` through Sphinx autodoc. The
checked-in HTML under [`docs/`](../docs/README.md) is a historical snapshot.

## Build the complete HTML guide

Use a separate Python 3.10 environment. From the repository root on macOS/Linux:

```sh
python3.10 -m venv ../negolog-docs-env
source ../negolog-docs-env/bin/activate
python -m pip install -r requirements.txt -r docs-source/requirements.txt
python -m sphinx -W --keep-going -b html docs-source ../negolog-docs-html
```

On Windows PowerShell, the direct interpreter path also works when shell
activation is unavailable:

```powershell
py -3.10 -m venv ../negolog-docs-env
..\negolog-docs-env\Scripts\python.exe -m pip install -r requirements.txt -r docs-source/requirements.txt
..\negolog-docs-env\Scripts\python.exe -m sphinx -W --keep-going -b html docs-source ../negolog-docs-html
```

Open `../negolog-docs-html/index.html` in your browser. The build includes
navigation, search, tutorials, figures, and the API reference. Output stays
outside the checkout; do not overwrite the historical HTML when editing sources.

The [Documentation workflow](../.github/workflows/docs.yml) runs the same strict
build and uploads a `negolog-api-documentation` artifact for review. After a
successful GitHub Actions run, download and extract that artifact and open
`index.html`. The workflow does not deploy the site or publish a release.

## Contribute a documentation change

Edit the relevant RST page or Python docstring, build the HTML, and inspect the
changed page. Try every modified command from the repository root. Keep example
outputs outside tracked source and input folders. See
[CONTRIBUTING.md](../CONTRIBUTING.md) for the full review workflow.

Autodoc imports library modules, so install runtime requirements as well as the
separate documentation requirements. Building does not run tournaments or call
external services. Sphinx is pinned; runtime dependency constraints are not a
complete lockfile. Record resolved dependency versions if an exact historical
rebuild matters.

The earlier RST exports remain in `docs/_sources/`. Current installation,
extension, model, and logging guidance lives here.
