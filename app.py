"""Run the local negotiation tournament and domain editor Web application."""
import importlib
import inspect
import json
import math
import os.path
import threading
from typing import Dict
from io import BytesIO
from pathlib import Path
from string import ascii_uppercase
from tempfile import TemporaryDirectory
from flask import Flask, request, jsonify, render_template, send_file
from flask_cors import CORS
import nenv
from domain_generator.domain_generator import generate_random_domain, generate_domain as generate_single_domain
from nenv import AbstractAgent
import yaml
import sys
import glob
from nenv.utils.DynamicImport import load_agent_class, load_estimator_class, load_logger_class
from nenv.utils.TournamentConfig import load_tournament_config
from domain_generator.domain_storage import domain_name, read_catalog, save_catalogued_domain, remove_domains as delete_domains
from nenv.utils.OSUtils import open_folder as utils_open_folder


app = Flask(__name__, template_folder="web_framework/", static_folder="web_framework/",
            static_url_path="")
app.config['SECRET_KEY'] = 'secret!'
CORS(app, resources={r"/*": {"origins": "*"}})

tournaments: Dict[str, nenv.Tournament] = {}
_state_lock = threading.RLock()
_running_tournaments = set()
_preview_images = {}


def _request_data():
    """Require a JSON object for mutation endpoints."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ValueError("Request must contain a JSON object.")
    return data


def _web_number(value, *, integer=False):
    """Accept finite numeric form strings without truncating fractional counts."""
    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
        raise ValueError("Numeric fields must contain a finite number.")
    number = float(value)
    if not math.isfinite(number) or (integer and not number.is_integer()):
        raise ValueError("Count fields must be integers; numeric fields must be finite.")
    return int(number) if integer else number


def _domain_response(row):
    """Preserve the domain table's existing response schema."""
    return {
        "RealName": str(row["DomainName"]), "DomainName": "Domain" + str(row["DomainName"]),
        "DomainSize": int(row["Size"]),
        "IssueValues": [float(value) for value in str(row["IssueValues"]).strip("[]").split(",")],
        "Opposition": f"{float(row['Opposition']):.3f}",
        "BalanceScore": f"{float(row['BalanceScore']):.3f}",
        **{key: float(row[key]) for key in ["ReservationValueA", "ReservationValueB", "MinUtility", "MaxUtility"]},
    }


def _require_idle():
    """Keep domain writes and global RNG settings out of active Web runs."""
    if _running_tournaments:
        raise ValueError("Wait for the active tournament to finish before changing domains or starting another run.")


def _web_configuration(source):
    """Normalize boolean select values emitted by the existing settings editor."""
    if isinstance(source, (str, Path)):
        with open(source, encoding="utf-8") as stream:
            source = yaml.safe_load(stream)
    if not isinstance(source, dict):
        raise ValueError("Tournament configuration must be a mapping.")
    config = dict(source)
    for field in ["shuffle", "self_negotiation"]:
        if isinstance(config.get(field), str) and config[field] in {"true", "false"}:
            config[field] = config[field] == "true"
    return config


def _configuration_path(value):
    """Resolve a configuration selected from the local settings directory."""
    path = Path(value)
    root = Path("tournament_configurations").resolve()
    if path.suffix != ".yaml" or path.resolve().parent != root or path.is_symlink():
        raise ValueError("Select a YAML file directly inside tournament_configurations.")
    return path


def _run_tournament(path, tournament):
    """Release the Web run slot even if an agent or logger fails."""
    try:
        tournament.run()
    except Exception as error:
        tournament.failure = str(error) or type(error).__name__
        app.logger.exception("Tournament failed: %s", path)
    finally:
        with _state_lock:
            _running_tournaments.discard(path)



@app.route("/", methods=["GET"])
def serve():
    """Serve the bundled local Web interface."""
    return render_template('index.html')


@app.route("/create/tournament_configuration", methods=["POST"])
def create_tournament():
    """Validate and save a reusable tournament configuration."""
    try:
        config = _web_configuration(_request_data()["config"])
        name = domain_name(config.pop("name")).replace(" ", "_")
        arguments, _drawing = load_tournament_config(config)
        nenv.Tournament(**arguments)
        root = Path("tournament_configurations")
        root.mkdir(exist_ok=True)
        file_path = root / (name + ".yaml")
        with TemporaryDirectory(prefix=".configuration-", dir=root) as temporary:
            staged = Path(temporary) / file_path.name
            staged.write_text(yaml.safe_dump(config), encoding="utf-8")
            staged.replace(file_path)
        return jsonify({"error": False, "message": f"Tournament settings saved: {file_path}"})
    except Exception as error:
        return jsonify({"error": True, "errorMessage": str(error)})


@app.route("/create/domains", methods=["POST"])
def create_domains():
    """Generate domains and register each successful result in the catalog."""
    try:
        config = dict(_request_data()["config"])
        count = _web_number(config.pop("numberOfDomains"), integer=True)
        if count < 1:
            raise ValueError("numberOfDomains must be positive.")
        name = domain_name(config["name"])
        config["is_for_genius"] = False
        config["domain_size_range"] = None
        for field in ["issue_size_range", "value_size_range", "utility_range", "opposition_range", "balance_score_range"]:
            if field in config and config[field] is not None:
                config[field] = [_web_number(value, integer=field in {"issue_size_range", "value_size_range"})
                                 for value in config[field]]
        for field in ["reservation_value_profile_a", "reservation_value_profile_b"]:
            if field in config:
                config[field] = _web_number(config[field])
        balance = config["balance_score_range"]
        config["value_boost"] = 0. if float(balance[0]) == 0 else sum(map(float, balance)) / 2.
        response = []
        with _state_lock:
            _require_idle()
            for index in range(count):
                config["name"] = name if count == 1 else f"{name}{index + 1}"
                result = save_catalogued_domain(generate_random_domain, **config)
                _preview_images.pop(result["DomainName"], None)
                response.append(_domain_response(result))
        return jsonify({"error": False, "domains": response})
    except Exception as error:
        return jsonify({"error": True, "errorMessage": str(error)})


@app.route("/fetch/agents", methods=["GET", "POST"])
def fetch_agents():
    """List concrete built-in agents using portable module paths."""
    try:
        agents = {}

        for file_name in sorted(glob.glob("agents/**/*.py", recursive=True)):
            module_path = file_name.replace("\\", "/").removesuffix(".py").replace("/", ".")
            module_path = module_path.removesuffix(".__init__")

            module = importlib.import_module(module_path)

            for key, value in module.__dict__.items():
                if inspect.isclass(value) and issubclass(value, AbstractAgent) and not inspect.isabstract(value):
                    agents[key] = module_path + "." + key

        return jsonify({"error": False, "agents": agents})
    except Exception as e:
        return jsonify({"error": True, "errorMessage": str(e)})


@app.route("/fetch/domains", methods=["GET", "POST"])
def fetch_domains():
    """Return the domain catalog in the existing Web table format."""
    try:
        response = [_domain_response(row) for _, row in read_catalog().iterrows()]
        return jsonify({"error": False, "domains": response})
    except Exception as error:
        return jsonify({"error": True, "errorMessage": str(error)})


@app.route("/fetch/tournament_configurations", methods=["GET", "POST"])
def fetch_tournament_configurations():
    """List valid settings and report invalid files separately."""
    settings, invalid = [], []
    for path in sorted(Path("tournament_configurations").glob("*.yaml")):
        try:
            with path.open(encoding="utf-8") as stream:
                config = _web_configuration(yaml.safe_load(stream))
            arguments, drawing = load_tournament_config(config)
            nenv.Tournament(**arguments)
            defaults = {"loggers": [], "estimators": [], "deadline_time": None, "deadline_round": None,
                        "self_negotiation": False, "repeat": 1, "result_dir": "results/", "seed": None,
                        "shuffle": False, "drawing_format": drawing}
            settings.append(dict(defaults, **config, name=path.as_posix()))
        except Exception as error:
            invalid.append({"name": str(path), "errorMessage": str(error)})
    return jsonify({"error": False, "settings": settings, "invalidSettings": invalid})


@app.route("/check/agent_path", methods=["POST"])
def check_agent_path():
    """Validate an agent class selected in the configuration editor."""
    try:
        class_path = _request_data()["path"]
        selected = load_agent_class(class_path)
        return jsonify({"error": False, "class_name": selected.__name__, "path": class_path})
    except Exception as error:
        return jsonify({"error": True, "errorMessage": str(error)})


@app.route("/check/logger_path", methods=["POST"])
def check_logger_path():
    """Validate a logger class selected in the configuration editor."""
    try:
        class_path = _request_data()["path"]
        selected = load_logger_class(class_path)
        return jsonify({"error": False, "class_name": selected.__name__, "path": class_path})
    except Exception as error:
        return jsonify({"error": True, "errorMessage": str(error)})


@app.route("/check/opp_model_path", methods=["POST"])
def check_opp_model_path():
    """Validate an opponent model selected in the configuration editor."""
    try:
        class_path = _request_data()["path"]
        selected = load_estimator_class(class_path)
        return jsonify({"error": False, "class_name": selected.__name__, "path": class_path})
    except Exception as error:
        return jsonify({"error": True, "errorMessage": str(error)})


@app.route("/remove/domains", methods=["POST"])
def remove_domains():
    """Remove selected domains and their matching catalog rows."""
    try:
        names = _request_data()["domainNames"]
        if not isinstance(names, list):
            raise ValueError("domainNames must be a list.")
        with _state_lock:
            _require_idle()
            delete_domains(names)
            for name in names:
                _preview_images.pop(str(name), None)
        return jsonify({"error": False})
    except Exception as error:
        return jsonify({"error": True, "errorMessage": str(error)})


@app.route("/remove/tournament_configuration", methods=["POST"])
def remove_tournament_setting():
    """Remove a settings file selected from the configuration directory."""
    try:
        path = _configuration_path(_request_data()["name"])
        path.unlink(missing_ok=True)
        return jsonify({"error": False})
    except Exception as error:
        return jsonify({"error": True, "errorMessage": str(error)})


@app.route("/start/tournament", methods=["POST"])
def start_tournament():
    """Reserve the Web run slot before starting a validated tournament."""
    try:
        path = _configuration_path(_request_data()["path"]).as_posix()
        with _state_lock:
            _require_idle()
            configuration, drawing = load_tournament_config(_web_configuration(path))
            tournament = nenv.Tournament(**configuration)
            nenv.utils.set_drawing_format(drawing)
            tournaments[path] = tournament
            _running_tournaments.add(path)
            try:
                threading.Thread(target=_run_tournament, args=(path, tournament), daemon=True).start()
            except Exception:
                _running_tournaments.discard(path)
                del tournaments[path]
                raise
        return jsonify({"error": False})
    except Exception as error:
        return jsonify({"error": True, "errorMessage": str(error)})


@app.route("/fetch/tournaments", methods=["POST", "GET"])
def fetch_tournaments():
    """Return pending, active, completed, cancelled and failed run status."""
    try:
        tournament_infos = []

        with _state_lock:
            snapshot = list(tournaments.items())
        for name, value in snapshot:
            tournament_info = {
                "name": name,
                "status": ("Error" if value.failure else "Cancelled" if value.cancelled else
                           "Active" if value.tournament_process.is_active else
                           "Finish" if value.tournament_process.is_completed else "Pending"),
                "completed_percentage": f"{'%.2f' % (value.tournament_process.completed_percentage * 100.)} %",
                "estimated_remaining_time": str(value.tournament_process.estimated_remaining_time)
                    if value.tournament_process.estimated_remaining_time is not None else "TBD",
                "elapsed_time": str(value.tournament_process.elapsed_time),
                "current": value.tournament_process.current_session,
                "last_update": (value.tournament_process.last_update_datetime.strftime('%Y-%m-%d %H:%M:%S')
                                if value.tournament_process.last_update_datetime else "TBD"),
                "start_time": (value.tournament_process.start_datetime.strftime('%Y-%m-%d %H:%M:%S')
                               if value.tournament_process.start_datetime else "TBD"),
                "errorMessage": value.failure,
                "result_dir": str(value.result_dir),
                "full_result_dir": os.path.join(os.getcwd(), value.result_dir)
            }

            tournament_infos.append(tournament_info)

        return jsonify({"error": False, "tournaments": tournament_infos})
    except Exception as e:
        return jsonify({"error": True, "errorMessage": str(e)})


@app.route("/remove/tournament", methods=["POST"])
def remove_tournament():
    """Request cancellation and remove the run from the displayed list."""
    try:
        path = _request_data()["path"]
        with _state_lock:
            if path not in tournaments:
                raise ValueError("Unknown tournament.")
            tournaments[path].killed = True
            del tournaments[path]
        return jsonify({"error": False})
    except Exception as error:
        return jsonify({"error": True, "errorMessage": str(error)})


@app.route("/open/folder", methods=["POST"])
def open_folder():
    """Open a requested local output folder in the file manager."""
    try:
        if "path" not in request.json:
            return jsonify({"error": True, "errorMessage": "Invalid request."})

        utils_open_folder(request.json["path"])

        return jsonify({"error": False})

    except Exception as e:
        return jsonify({"error": True, "errorMessage": str(e)})


@app.route("/fetch/profiles", methods=["POST"])
def fetch_profiles():
    """Load saved profiles and discard an earlier unsaved image preview."""
    try:
        if "name" not in request.json:
            return jsonify({"error": True, "errorMessage": "Invalid request."})

        name = domain_name(_request_data()["name"])
        path = f"domains/{name}/"
        with _state_lock:
            _preview_images.pop(name.removeprefix("domain"), None)

        if not os.path.exists(path):
            return jsonify({"error": True, "errorMessage": "Domain folder cannot be found: " + path})

        profiles = {}

        with open(os.path.join(path, "profileA.json"), "r") as f:
            profiles["ProfileA"] = json.load(f)

        with open(os.path.join(path, "profileB.json"), "r") as f:
            profiles["ProfileB"] = json.load(f)

        with open(os.path.join(path, "specs.json"), "r") as f:
            specs = json.load(f)

        return jsonify({"error": False, "profiles": profiles, "specs": specs})

    except Exception as e:
        return jsonify({"error": True, "errorMessage": str(e)})


@app.route("/fetch/bid_space/<domain>", methods=["POST", "GET"])
def fetch_bid_space(domain):
    """Serve a temporary preview or the saved domain image without caching."""
    name = domain_name(domain)
    with _state_lock:
        preview = _preview_images.get(name.removeprefix("domain"))
    source = BytesIO(preview) if preview is not None else os.path.abspath(f"domains/{name}/bid_space.png")
    response = send_file(source, mimetype="image/png", max_age=0)
    response.headers["Cache-Control"] = "no-store"
    return response


@app.route("/create/domain", methods=["POST"])
def create_domain():
    """Create a manual domain and add it to the catalog."""
    try:
        data = _request_data()
        count = _web_number(data["numberOfIssues"], integer=True)
        if not 1 <= count <= 26:
            raise ValueError("numberOfIssues must be between 1 and 26.")
        issues = [f"Issue{letter}" for letter in ascii_uppercase[:count]]
        weights_a = {issue: index + 1 for index, issue in enumerate(issues)}
        weights_b = {issue: count - index for index, issue in enumerate(issues)}
        values_a, values_b = {}, {}
        for index, issue in enumerate(issues):
            size = _web_number(data["numberOfValuesPerIssue"][str(index)], integer=True)
            if not 1 <= size <= 26:
                raise ValueError("Each issue must have between 1 and 26 values.")
            values_a[issue] = {f"Value{ascii_uppercase[j]}": round(1. - j / size, 3) for j in range(size)}
            values_b[issue] = {f"Value{ascii_uppercase[j]}": round((j + 1) / size, 3) for j in range(size)}
        with _state_lock:
            _require_idle()
            result = save_catalogued_domain(generate_single_domain, data["name"], weights_a, weights_b, values_a, values_b)
            _preview_images.pop(result["DomainName"], None)
        return jsonify({"error": False, "result": result})
    except Exception as error:
        return jsonify({"error": True, "errorMessage": str(error)})


@app.route("/edit/domain", methods=["POST"])
def edit_domain():
    """Preview profiles without saving, or explicitly publish the edited domain."""
    try:
        data = _request_data()
        if not isinstance(data["save"], bool):
            raise ValueError("save must be a JSON boolean.")
        profile_a, profile_b = data["profileA"], data["profileB"]
        name = domain_name(data["name"])
        arguments = (name, profile_a["issueWeights"], profile_b["issueWeights"], profile_a["issues"],
                     profile_b["issues"], profile_a["reservationValue"], profile_b["reservationValue"])
        with _state_lock:
            _require_idle()
            if data["save"]:
                result = save_catalogued_domain(generate_single_domain, *arguments)
                _preview_images.pop(name, None)
                return jsonify({"error": False, "domains": [_domain_response(result)]})
            with TemporaryDirectory(prefix="negolog-preview-") as temporary:
                result = generate_single_domain(*arguments, output_dir=temporary)
                _preview_images[name] = (Path(temporary) / ("domain" + name) / "bid_space.png").read_bytes()
            return jsonify({"error": False, "result": result})
    except Exception as error:
        return jsonify({"error": True, "errorMessage": str(error)})


if __name__ == "__main__":
    if len(sys.argv) > 1:
        if len(sys.argv) == 3 and sys.argv[1] in ['-p', '-port']:
            port = int(sys.argv[2])
        else:
            print("Unknown command! Examples:")
            print("\tpython app.py")
            print("\tpython app.py -p 5000")
            print("\tpython app.py -port 5000")

            exit(1)
    else:
        port = 5000

    app.run(port=port, threaded=True)
