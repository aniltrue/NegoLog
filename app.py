import importlib
import json
import os.path
import shutil
import threading
from typing import Dict
import pandas as pd
from flask import Flask, request, jsonify, render_template, send_file
from flask_cors import CORS
import nenv
from domain_generator.domain_generator import generate_random_domain, generate_domain as generate_single_domain
from nenv import AbstractAgent
import yaml
import sys
import glob
from nenv.OpponentModel import AbstractOpponentModel
from nenv.logger import AbstractLogger
from nenv.utils.DynamicImport import load_agent_class, load_estimator_class, load_logger_class
from nenv.utils.OSUtils import open_folder as utils_open_folder


app = Flask(__name__, template_folder="web_framework/", static_folder="web_framework/",
            static_url_path="")
app.config['SECRET_KEY'] = 'secret!'
CORS(app, resources={r"/*": {"origins": "*"}})

tournaments: Dict[str, nenv.Tournament] = {}


@app.route("/", methods=["GET"])
def serve():
    return render_template('index.html')


@app.route("/create/tournament_configuration", methods=["POST"])
def create_tournament():
    if not os.path.exists("tournament_configurations/"):
        os.makedirs("tournament_configurations/")

    config = request.json["config"]
    file_path = f"tournament_configurations/{str(config['name']).replace(' ', '_')}.yaml"

    del config["name"]

    with open(file_path, "w") as f:
        yaml.safe_dump(config, f)

    return jsonify({"error": False,
                    "message": f"Tournament Settings are successfully created: `{file_path}`\nYou can run tournament such as: `python run.py {file_path}`"})


@app.route("/create/domains", methods=["POST"])
def create_domains():
    try:
        if "config" not in request.json:
            return jsonify({"error": True, "errorMessage": "Invalid request."})

        config = request.json["config"]
        config["is_for_genius"] = False
        config["domain_size_range"] = None

        domains = pd.read_excel("domains/domains.xlsx", sheet_name="domains")

        response = []

        value_boost = 0. if float(config["balance_score_range"][0]) == 0 else \
            (float(config["balance_score_range"][0]) + float(config["balance_score_range"][1])) / 2.

        config["value_boost"] = value_boost

        if int(config["numberOfDomains"]) == 1:
            del config["numberOfDomains"]

            result = generate_random_domain(**config)

            domains = domains[domains["DomainName"] != result["DomainName"]]
            domains.loc[len(domains)] = result

            domains = domains.loc[:, ~domains.columns.str.contains('^Unnamed')]
            domains.to_excel("domains/domains.xlsx", sheet_name="domains", index=False)

            response.append({
                "RealName": str(result["DomainName"]),
                "DomainName": "Domain%s" % result["DomainName"],
                "DomainSize": int(result["Size"]),
                "IssueValues": [float(v) for v in
                                str(result["IssueValues"]).replace("[", "").replace("]", "").split(",")],
                "Opposition": "%.3f" % round(float(result["Opposition"]), 3),
                "BalanceScore": "%.3f" % round(float(result["BalanceScore"]), 3),
                "ReservationValueA": float(result["ReservationValueA"]),
                "ReservationValueB": float(result["ReservationValueB"]),
                "MinUtility": float(result["MinUtility"]),
                "MaxUtility": float(result["MaxUtility"])
            })

            return jsonify({"error": False, "domains": response})
        else:
            name = config["name"]

            number_of_domains = int(config["numberOfDomains"])

            del config["numberOfDomains"]

            for i in range(number_of_domains):
                config["name"] = f"{name}{i + 1}"

                result = generate_random_domain(**config)

                domains = domains[domains["DomainName"] != result["DomainName"]]
                domains.loc[len(domains)] = result

                response.append({
                    "RealName": str(result["DomainName"]),
                    "DomainName": "Domain%s" % result["DomainName"],
                    "DomainSize": int(result["Size"]),
                    "IssueValues": [float(v) for v in
                                    str(result["IssueValues"]).replace("[", "").replace("]", "").split(",")],
                    "Opposition": "%.3f" % round(float(result["Opposition"]), 3),
                    "BalanceScore": "%.3f" % round(float(result["BalanceScore"]), 3),
                    "ReservationValueA": float(result["ReservationValueA"]),
                    "ReservationValueB": float(result["ReservationValueB"]),
                    "MinUtility": float(result["MinUtility"]),
                    "MaxUtility": float(result["MaxUtility"])
                })

            domains = domains.loc[:, ~domains.columns.str.contains('^Unnamed')]
            domains.to_excel("domains/domains.xlsx", sheet_name="domains", index=False)

            return jsonify({"error": False, "domains": response})

    except Exception as e:
        return jsonify({"error": True, "errorMessage": str(e)})

@app.route("/fetch/agents", methods=["GET", "POST"])
def fetch_agents():
    try:
        agents = {}

        for file_name in glob.glob("agents/**/*.py", recursive=True):
            if "ParetoWalker" in file_name or "NegoFormer" in file_name:
                continue

            module_path = file_name.replace("\\__init__", "").replace("\\", ".").replace(".py", "")

            module = importlib.import_module(module_path)

            for key, value in module.__dict__.items():
                if str(type(value)) == "<class 'abc.ABCMeta'>" and issubclass(value, AbstractAgent):
                    agents[key] = module_path + "." + key

        return jsonify({"error": False, "agents": agents})
    except Exception as e:
        return jsonify({"error": True, "errorMessage": str(e)})


@app.route("/fetch/domains", methods=["GET", "POST"])
def fetch_domains():
    try:
        domains = pd.read_excel("domains/domains.xlsx", sheet_name="domains")

        response = []

        for i, row in domains.iterrows():
            response.append({
                "RealName": str(row["DomainName"]),
                "DomainName": "Domain%s" % row["DomainName"],
                "DomainSize": int(row["Size"]),
                "IssueValues": [float(v) for v in str(row["IssueValues"]).replace("[", "").replace("]", "").split(",")],
                "Opposition": "%.3f" % round(float(row["Opposition"]), 3),
                "BalanceScore": "%.3f" % round(float(row["BalanceScore"]), 3),
                "ReservationValueA": float(row["ReservationValueA"]),
                "ReservationValueB": float(row["ReservationValueB"]),
                "MinUtility": float(row["MinUtility"]),
                "MaxUtility": float(row["MaxUtility"])
            })

        return jsonify({"error": False, "domains": response})
    except Exception as e:
        return jsonify({"error": True, "errorMessage": str(e)})


@app.route("/fetch/tournament_configurations", methods=["GET", "POST"])
def fetch_tournament_configurations():
    try:
        if not os.path.exists("tournament_configurations/"):
            return jsonify({"error": False, "settings": []})

        config_files = []

        for file_name in glob.glob("tournament_configurations/*.yaml", recursive=True):
            with open(file_name, "r") as f:
                file = yaml.safe_load(f)

            if "agents" in file and "deadline_time" in file and "deadline_round" in file and "domains" in file and "loggers" in file and "estimators" in file and "self_negotiation" in file and "repeat" in file and "result_dir" in file and "seed" in file and "shuffle" in file and "drawing_format" in file:
                file["name"] = file_name
                config_files.append(file)

        return jsonify({"error": False, "settings": config_files})

    except Exception as e:
        return jsonify({"error": True, "errorMessage": str(e), "settings": []})


@app.route("/check/agent_path", methods=["POST"])
def check_agent_path():
    try:
        if "path" not in request.json:
            return jsonify({"error": True, "errorMessage": "Invalid request."})

        class_path = str(request.json["path"])

        modules = class_path.split(".")

        path = ".".join(modules[:-1])
        class_name = modules[-1]

        agent_class = getattr(importlib.import_module(path), class_name)

        if issubclass(agent_class, AbstractAgent):
            return jsonify({"error": False, "class_name": class_name, "path": class_path})
        else:
            return jsonify({"error": True, "errorMessage": "Each agent must be sub-class of `AbstractAgent` class."})
    except Exception as e:
        return jsonify({"error": True, "errorMessage": str(e)})


@app.route("/check/logger_path", methods=["POST"])
def check_logger_path():
    try:
        if "path" not in request.json:
            return jsonify({"error": True, "errorMessage": "Invalid request."})

        class_path = str(request.json["path"])

        modules = class_path.split(".")

        path = ".".join(modules[:-1])
        class_name = modules[-1]

        logger_class = getattr(importlib.import_module(path), class_name)

        if issubclass(logger_class, AbstractLogger):
            return jsonify({"error": False, "class_name": class_name, "path": class_path})
        else:
            return jsonify({"error": True, "errorMessage": "Each logger must be sub-class of `AbstractLogger` class."})
    except Exception as e:
        return jsonify({"error": True, "errorMessage": str(e)})


@app.route("/check/opp_model_path", methods=["POST"])
def check_opp_model_path():
    try:
        if "path" not in request.json:
            return jsonify({"error": True, "errorMessage": "Invalid request."})

        class_path = str(request.json["path"])

        modules = class_path.split(".")

        path = ".".join(modules[:-1])
        class_name = modules[-1]

        opp_model_class = getattr(importlib.import_module(path), class_name)

        if issubclass(opp_model_class, AbstractOpponentModel):
            return jsonify({"error": False, "class_name": class_name, "path": class_path})
        else:
            return jsonify({"error": True,
                            "errorMessage": "Each opponent model must be sub-class of `AbstractOpponentModel` class."})
    except Exception as e:
        return jsonify({"error": True, "errorMessage": str(e)})


@app.route("/remove/domains", methods=["POST"])
def remove_domains():
    try:
        if "domainNames" not in request.json:
            return jsonify({"error": True, "errorMessage": "Invalid request."})

        domain_names = request.json["domainNames"]

        domains = pd.read_excel("domains/domains.xlsx", sheet_name="domains")

        for domain in domain_names:
            if os.path.exists(f"domains/domain{domain}/"):
                shutil.rmtree(f"domains/domain{domain}/")

            domains = domains[domains["DomainName"] != domain]

        domains.to_excel("domains/domains.xlsx", sheet_name="domains", index=False)

        return jsonify({"error": False})

    except Exception as e:
        return jsonify({"error": True, "errorMessage": str(e)})


@app.route("/remove/tournament_configuration", methods=["POST"])
def remove_tournament_setting():
    try:
        if "name" not in request.json:
            return jsonify({"error": True, "errorMessage": "Invalid request."})

        if os.path.exists(request.json["name"]):
            os.remove(request.json["name"])

        return jsonify({"error": False})

    except Exception as e:
        return jsonify({"error": True, "errorMessage": str(e)})


@app.route("/start/tournament", methods=["POST"])
def start_tournament():
    try:
        if "path" not in request.json:
            return jsonify({"error": True, "errorMessage": "Invalid request."})

        tournament_configuration_path = request.json["path"]

        if not os.path.exists(tournament_configuration_path):
            return jsonify({"error": True, "errorMessage": "Tournament Setting cannot be found."})

        with open(tournament_configuration_path, "r") as f:
            configuration = yaml.safe_load(f)

        configuration["agent_classes"] = set([load_agent_class(path) for path in configuration["agents"]])
        configuration["logger_classes"] = set([load_logger_class(path) for path in configuration["loggers"]])
        configuration["estimator_classes"] = set([load_estimator_class(path) for path in configuration["estimators"]])

        del configuration["agents"]
        del configuration["loggers"]
        del configuration["estimators"]

        # Update drawing style
        nenv.utils.set_drawing_format(configuration["drawing_format"])

        del configuration["drawing_format"]

        tournament = nenv.Tournament(**configuration)

        tournaments[tournament_configuration_path] = tournament

        thread = threading.Thread(target=lambda: tournament.run())
        thread.daemon = True
        thread.start()

        return jsonify({"error": False})

    except Exception as e:
        return jsonify({"error": True, "errorMessage": str(e)})


@app.route("/fetch/tournaments", methods=["POST", "GET"])
def fetch_tournaments():
    try:
        tournament_infos = []

        for name, value in tournaments.items():
            tournament_info = {
                "name": name,
                "status": "Active" if value.tournament_process.is_active else "Finish",
                "completed_percentage": f"{'%.2f' % (value.tournament_process.completed_percentage * 100.)} %",
                "estimated_remaining_time": str(value.tournament_process.estimated_remaining_time)
                    if value.tournament_process.estimated_remaining_time is not None else "TBD",
                "elapsed_time": str(value.tournament_process.elapsed_time),
                "current": value.tournament_process.current_session,
                "last_update": str(value.tournament_process.last_update_datetime.strftime('%Y-%m-%d %H:%M:%S')),
                "start_time": str(value.tournament_process.start_datetime.strftime('%Y-%m-%d %H:%M:%S')),
                "result_dir": value.result_dir,
                "full_result_dir": os.path.join(os.getcwd(), value.result_dir)
            }

            tournament_infos.append(tournament_info)

        return jsonify({"error": False, "tournaments": tournament_infos})
    except Exception as e:
        return jsonify({"error": True, "errorMessage": str(e)})


@app.route("/remove/tournament", methods=["POST"])
def remove_tournament():
    try:
        if "path" not in request.json:
            return jsonify({"error": True, "errorMessage": "Invalid request."})

        tournament_path = request.json["path"]

        if tournament_path not in tournaments:
            return jsonify({"error": True, "errorMessage": "Unknown tournament."})

        tournaments[tournament_path].killed = True

        del tournaments[tournament_path]

        return jsonify({"error": False})

    except Exception as e:
        return jsonify({"error": True, "errorMessage": str(e)})


@app.route("/open/folder", methods=["POST"])
def open_folder():
    try:
        if "path" not in request.json:
            return jsonify({"error": True, "errorMessage": "Invalid request."})

        utils_open_folder(request.json["path"])

        return jsonify({"error": False})

    except Exception as e:
        return jsonify({"error": True, "errorMessage": str(e)})


@app.route("/fetch/profiles", methods=["POST"])
def fetch_profiles():
    try:
        if "name" not in request.json:
            return jsonify({"error": True, "errorMessage": "Invalid request."})

        path = f"domains/{request.json['name']}/"

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
    path = f"domains/{domain}/"

    return send_file(os.path.join(path, "bid_space.png"), mimetype="image/png")


@app.route("/create/domain", methods=["POST"])
def create_domain():
    try:
        from string import ascii_uppercase

        if "name" not in request.json or "numberOfIssues" not in request.json or "numberOfValuesPerIssue" not in request.json:
            return jsonify({"error": True, "errorMessage": "Invalid request."})

        number_of_issues = int(request.json["numberOfIssues"])

        issues = [f"Issue{ascii_uppercase[i]}" for i in range(number_of_issues)]
        issue_weights_a = {issues[i]: i + 1 for i in range(number_of_issues)}
        issue_weights_a = {issues[i]: round(issue_weights_a[issues[i]] / sum(issue_weights_a.values()), 3) for i in range(number_of_issues)}

        issue_weights_b = {issues[i]: number_of_issues - i for i in range(number_of_issues)}
        issue_weights_b = {issues[i]: round(issue_weights_b[issues[i]] / sum(issue_weights_b.values()), 3) for i in range(number_of_issues)}

        issues_a = {}
        issues_b = {}

        for i in range(number_of_issues):
            issue_name = issues[i]

            number_of_values = int(request.json["numberOfValuesPerIssue"][str(i)])

            step_size = 1. / number_of_values

            issues_a[issue_name] = {}
            issues_b[issue_name] = {}

            for j in range(number_of_values):
                value_name = f"Value{ascii_uppercase[j]}"

                issues_a[issue_name][value_name] = round(1. - (step_size * j), 3)
                issues_b[issue_name][value_name] = round(step_size * (j + 1), 3)

        result = generate_single_domain(request.json["name"], issue_weights_a, issue_weights_b, issues_a, issues_b, 0., 0.)

        return jsonify({"error": False, "result": result})

    except Exception as e:
        return jsonify({"error": True, "errorMessage": str(e)})


@app.route("/edit/domain", methods=["POST"])
def edit_domain():
    try:
        if "name" not in request.json or "profileA" not in request.json or "profileB" not in request.json or "save" not in request.json:
            return jsonify({"error": True, "errorMessage": "Invalid request."})

        profile_a = request.json["profileA"]
        profile_b = request.json["profileB"]

        result = generate_single_domain(request.json["name"], profile_a["issueWeights"], profile_b["issueWeights"], profile_a["issues"], profile_b["issues"], profile_a["reservationValue"], profile_b["reservationValue"])

        if bool(request.json["save"]):
            domains = pd.read_excel("domains/domains.xlsx", sheet_name="domains")

            domains = domains[domains["DomainName"] != "name"]
            domains.loc[len(domains)] = result

            domains = domains.loc[:, ~domains.columns.str.contains('^Unnamed')]
            domains.to_excel("domains/domains.xlsx", sheet_name="domains", index=False)

            response = []

            response.append({
                "RealName": str(result["DomainName"]),
                "DomainName": "Domain%s" % result["DomainName"],
                "DomainSize": int(result["Size"]),
                "IssueValues": [float(v) for v in
                                str(result["IssueValues"]).replace("[", "").replace("]", "").split(",")],
                "Opposition": "%.3f" % round(float(result["Opposition"]), 3),
                "BalanceScore": "%.3f" % round(float(result["BalanceScore"]), 3),
                "ReservationValueA": float(result["ReservationValueA"]),
                "ReservationValueB": float(result["ReservationValueB"]),
                "MinUtility": float(result["MinUtility"]),
                "MaxUtility": float(result["MaxUtility"])
            })

            return jsonify({"error": False, "domains": response})
        else:
            return jsonify({"error": False, "result": result})

    except Exception as e:
        return jsonify({"error": True, "errorMessage": str(e)})


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
