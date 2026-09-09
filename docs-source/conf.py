"""Build the current public API from this checkout with Sphinx."""
from pathlib import Path
import re
import sys


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

project = "NegoLog"
author = "NegoLog contributors"
extensions = ["sphinx.ext.autodoc"]
root_doc = "index"
html_theme = "alabaster"
html_title = "NegoLog — current API"
autodoc_member_order = "bysource"
autodoc_typehints = "signature"
exclude_patterns = ["README.md"]


def namespace_citations(_app, _what, name, _obj, _options, lines):
    """Keep repeated source citations local to each documented object's text."""
    prefix = name.replace(".", "-")
    labels = []
    for line in lines:
        match = re.match(r"^\s*\.\. \[([A-Za-z][\w-]*)\]", line)
        if match:
            labels.append(match.group(1))
    for index, line in enumerate(lines):
        for label in labels:
            line = line.replace(f"[{label}]", f"[{prefix}-{label}]")
        lines[index] = line


def setup(app):
    """Preserve citation text without duplicate global labels in autodoc pages."""
    app.connect("autodoc-process-docstring", namespace_citations)
