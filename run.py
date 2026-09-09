import os.path
import sys
import warnings
import nenv
from nenv.utils.TournamentConfig import load_tournament_config

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
        configuration, drawing_format = load_tournament_config(tournament_configuration_path)
        tournament = nenv.Tournament(**configuration)
        nenv.utils.set_drawing_format(drawing_format)
        tournament.run()
    except Exception as exc:
        print(f"Tournament failed: {exc}", file=sys.stderr)
        sys.exit(1)
