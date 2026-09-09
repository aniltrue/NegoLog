"""Load the same validated tournament configuration for the CLI and Web UI."""
import copy
from pathlib import Path

import yaml

from nenv.utils.DynamicImport import load_agent_class, load_estimator_class, load_logger_class


def load_tournament_config(source):
    """Return constructor arguments and drawing format without mutating input."""
    if isinstance(source, (str, Path)):
        with open(source, encoding="utf-8") as stream:
            configuration = yaml.safe_load(stream)
    else:
        configuration = copy.deepcopy(source)
    if not isinstance(configuration, dict):
        raise ValueError("Tournament configuration must be a YAML mapping.")
    allowed = {"agents", "domains", "estimators", "loggers", "deadline_time", "deadline_round",
               "self_negotiation", "repeat", "result_dir", "seed", "shuffle", "drawing_format"}
    unknown = set(configuration) - allowed
    if unknown:
        raise ValueError("Unknown configuration fields: " + ", ".join(sorted(map(str, unknown))))
    for field in ["agents", "domains"]:
        if not isinstance(configuration.get(field), list) or not configuration[field]:
            raise ValueError(f"{field} must be a nonempty list.")
    for field in ["loggers", "estimators"]:
        configuration.setdefault(field, [])
        if not isinstance(configuration[field], list):
            raise ValueError(f"{field} must be a list.")
    configuration.setdefault("deadline_time", None)
    configuration.setdefault("deadline_round", None)
    drawing = configuration.pop("drawing_format", "matplotlib-PNG")
    if drawing not in {"matplotlib-PNG", "matplotlib-SVG", "plotly"}:
        raise ValueError("drawing_format must be matplotlib-PNG, matplotlib-SVG or plotly.")
    for field, target, loader in [("agents", "agent_classes", load_agent_class),
                                  ("estimators", "estimator_classes", load_estimator_class),
                                  ("loggers", "logger_classes", load_logger_class)]:
        configuration[target] = [loader(path) for path in configuration.pop(field)]
    return configuration, drawing
