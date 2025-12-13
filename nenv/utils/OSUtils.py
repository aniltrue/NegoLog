import os
import subprocess
import platform


def open_folder(directory: str):
    """
    This method shows the directory

    :param directory: The directory to open
    """
    # Get the absolute path
    path = os.path.realpath(os.path.join(os.getcwd(), directory))

    if platform.system() == "Windows":
        os.startfile(path)
    elif platform.system() == "Darwin":  # macOS
        subprocess.call(["open", path])
    elif platform.system() == "Linux":
        subprocess.call(["xdg-open", path])
    else:
        raise OSError(f"Unsupported operating system: {platform.system()}")
