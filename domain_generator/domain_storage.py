"""Validate domain data and publish complete domain folders and catalogs."""
from functools import wraps
import inspect
import math
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory
import threading

import pandas as pd


_generation_lock = threading.RLock()


def domain_name(value):
    """Return a portable single-component domain identifier."""
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        raise ValueError("Domain name must be a string or integer identifier.")
    name = str(value).strip()
    if not name or name in {".", ".."} or any(c in name for c in '/\\\0<>:"|?*'):
        raise ValueError("Domain name must be a nonempty, portable folder name.")
    return name


def validate_profiles(weights_a, weights_b, issues_a, issues_b, reservation_a, reservation_b):
    """Reject incompatible or nonfinite profiles before writing any files."""
    for weights, issues, reservation in [(weights_a, issues_a, reservation_a),
                                         (weights_b, issues_b, reservation_b)]:
        if not isinstance(weights, dict) or not weights or not isinstance(issues, dict):
            raise ValueError("Profiles require nonempty issue weights and values.")
        if set(weights) != set(issues):
            raise ValueError("Issue weights and issue values must have the same keys.")
        if any(not isinstance(issue, str) or not issue for issue in issues):
            raise ValueError("Issue names must be nonempty strings.")
        numbers = list(weights.values())
        for values in issues.values():
            if not isinstance(values, dict) or not values:
                raise ValueError("Each issue must contain at least one value.")
            if any(not isinstance(value, str) or not value for value in values):
                raise ValueError("Value names must be nonempty strings.")
            numbers.extend(values.values())
        if any(isinstance(number, bool) or not isinstance(number, (int, float))
               or not math.isfinite(number) or number < 0 for number in numbers):
            raise ValueError("Profile weights must be finite nonnegative numbers.")
        if sum(weights.values()) <= 0:
            raise ValueError("Issue weights must have a positive sum.")
        if isinstance(reservation, bool) or not isinstance(reservation, (int, float)) or not math.isfinite(reservation):
            raise ValueError("Reservation values must be finite numbers.")
    if set(issues_a) != set(issues_b) or any(set(issues_a[key]) != set(issues_b[key]) for key in issues_a):
        raise ValueError("Both profiles must describe the same issues and values.")


def atomic_domain_output(function):
    """Stage a generator's output and retain the old domain if generation fails."""
    signature = inspect.signature(function)

    @wraps(function)
    def generate(*args, **kwargs):
        bound = signature.bind(*args, **kwargs)
        bound.apply_defaults()
        name = domain_name(bound.arguments["name"])
        bound.arguments["name"] = name
        default_root = "domains_genius" if bound.arguments.get("is_for_genius") else "domains"
        root = Path(bound.arguments.get("output_dir") or default_root).resolve()
        root.mkdir(parents=True, exist_ok=True)
        target = root / ("domain" + name)
        if target.is_symlink() or (target.exists() and not target.is_dir()):
            raise ValueError("The domain output must be a directory, not a file or symlink.")
        with _generation_lock, TemporaryDirectory(prefix=".domain-stage-", dir=root) as temporary:
            bound.arguments["output_dir"] = temporary
            result = function(*bound.args, **bound.kwargs)
            staged = Path(temporary) / target.name
            previous = Path(temporary) / "previous"
            if target.exists():
                target.replace(previous)
            try:
                staged.replace(target)
            except OSError:
                if previous.exists():
                    previous.replace(target)
                raise
            return result

    return generate


def read_catalog(path="domains/domains.xlsx"):
    """Read domain IDs as strings, preserving names such as 001."""
    if not Path(path).exists():
        return pd.DataFrame(columns=["DomainName"])
    frame = pd.read_excel(path, sheet_name="domains", dtype={"DomainName": str})
    if "DomainName" not in frame:
        raise ValueError("The domain catalog is missing its DomainName column.")
    return frame.loc[:, ~frame.columns.str.startswith("Unnamed")]


def write_catalog(frame, path="domains/domains.xlsx"):
    """Replace the catalog only after a complete workbook has been written."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix=".catalog-stage-", dir=target.parent) as temporary:
        staged = Path(temporary) / target.name
        frame.to_excel(staged, sheet_name="domains", index=False)
        staged.replace(target)


def upsert_catalog(result, path="domains/domains.xlsx"):
    """Update one domain without dropping other rows or duplicating its ID."""
    frame = read_catalog(path)
    name = domain_name(result["DomainName"])
    frame = frame[frame["DomainName"] != name]
    row = dict(result, DomainName=name)
    if frame.empty:
        updated = pd.DataFrame([row])
    else:
        updated = pd.concat([frame, pd.DataFrame([row])], ignore_index=True)
    write_catalog(updated, path)


def remove_domains(names, path="domains/domains.xlsx"):
    """Remove validated domain folders and their catalog rows."""
    names = [domain_name(name) for name in names]
    frame = read_catalog(path)
    root = Path(path).parent
    for name in names:
        target = root / ("domain" + name)
        if target.is_symlink():
            raise ValueError("Refusing to remove a symlink as a domain folder.")
    with _generation_lock, TemporaryDirectory(prefix=".domain-remove-", dir=root) as temporary:
        moved = []
        try:
            for name in dict.fromkeys(names):
                target = root / ("domain" + name)
                if target.exists():
                    backup = Path(temporary) / target.name
                    target.replace(backup)
                    moved.append((target, backup))
            write_catalog(frame[~frame["DomainName"].isin(names)], path)
        except Exception:
            for target, backup in reversed(moved):
                backup.replace(target)
            raise


def save_catalogued_domain(generator, *args, **kwargs):
    """Publish a Web domain and its catalog, rolling back on write failure."""
    root = Path("domains")
    root.mkdir(exist_ok=True)
    with _generation_lock, TemporaryDirectory(prefix=".domain-save-", dir=root) as temporary:
        staged_root = Path(temporary)
        kwargs["output_dir"] = staged_root
        result = generator(*args, **kwargs)
        name = "domain" + domain_name(result["DomainName"])
        target = root / name
        if target.is_symlink() or (target.exists() and not target.is_dir()):
            raise ValueError("The domain output must be a directory, not a file or symlink.")
        catalog = root / "domains.xlsx"
        staged_catalog = staged_root / catalog.name
        if catalog.exists():
            shutil.copy2(catalog, staged_catalog)
        upsert_catalog(result, staged_catalog)
        previous = staged_root / "previous"
        if target.exists():
            target.replace(previous)
        published = False
        try:
            (staged_root / name).replace(target)
            published = True
            staged_catalog.replace(catalog)
        except OSError:
            if published:
                shutil.rmtree(target)
            if previous.exists():
                previous.replace(target)
            raise
        return result
