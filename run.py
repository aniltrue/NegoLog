import os.path
import sys
import warnings
import yaml
import nenv
from nenv.utils.DynamicImport import load_logger_class, load_estimator_class, load_agent_class

if not sys.warnoptions:
    warnings.simplefilter("ignore", category=DeprecationWarning)
    warnings.simplefilter("ignore", category=FutureWarning)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Tournament configuration is not specified. Instead, try this:")
        print("python run.py tournament_example.yaml")

        exit(1)

    tournament_configuration_path = sys.argv[1]

    if not os.path.exists(tournament_configuration_path):
        print(f"File ({tournament_configuration_path}) cannot be found!")

        exit(1)

    try:
        with open(tournament_configuration_path, "r") as f:
            configuration = yaml.safe_load(f)
    except yaml.YAMLError as exc:
        print(exc)

        exit(1)

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
    tournament.run()
