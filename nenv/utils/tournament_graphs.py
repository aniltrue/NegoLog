"""
    Helpful draw functions for loggers.
"""
import os
from typing import Union, List, Dict

import matplotlib.pyplot as plt
import plotly.express as px
import plotly.figure_factory as ff
import plotly
import seaborn as sb
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Agg backend for file-based rendering

DRAWING_FORMAT: str = None


def set_drawing_format(drawing_format: str):
    """
        Change the *DRAWING_FORMAT* for the loggers

        **Possible Values**:
            - **matplotlib-PNG**: Utilizing *matplotlib* and saving as *png* image format
            - **matplotlib-SVG**: Utilizing *matplotlib* and saving as *svg* image format
            - **plotly**: Utilizing *plotly* and saving as interactive *html*

        :param drawing_format: New drawing format.
        :return: Nothing
    """

    assert drawing_format in ["matplotlib-PNG", "matplotlib-SVG", "plotly"], "Unknown drawing format"

    global DRAWING_FORMAT

    DRAWING_FORMAT = drawing_format
    os.environ['DRAWING_FORMAT'] = drawing_format


def draw_heatmap_matplotlib(data: np.ndarray, labels_x: list, labels_y: list, save_path: str, x_axis_name: str, y_axis_name: str, title: str, fmt: str = ".2f", file_format: str = "png", **kwargs):
    fig = plt.figure(figsize=(len(labels_x) + 2, len(labels_y)), facecolor="white", dpi=1200)
    ax = fig.gca()

    data = np.array(data, dtype=np.float32)

    # Color scale
    if "reverse" in kwargs and kwargs["reverse"]:
        cp = sb.color_palette("rocket_r", as_cmap=True)
    else:
        cp = sb.color_palette("rocket", as_cmap=True)

    # Min-Max values
    vmax = 1.
    vmin = 0.

    if "auto_scale" in kwargs and kwargs["auto_scale"]:
        if None in data:
            vmax = max(max([data[i, j] for j in range(data.shape[1]) if data[i, j] is not None]) for i in range(data.shape[1]))
            vmin = min(min([data[i, j] for j in range(data.shape[1]) if data[i, j] is not None]) for i in range(data.shape[1]))
        else:
            vmax = np.max(data)
            vmin = np.min(data)

    # Draw
    hm = sb.heatmap(data=data, annot=True, fmt=fmt, xticklabels=labels_x, yticklabels=labels_y,
                    vmin=vmin, vmax=vmax, ax=ax, square=False, cmap=cp, annot_kws={"fontsize": 16, "weight": "bold"})

    hm.set_facecolor("dimgray")
    hm.set_xticklabels(hm.get_xticklabels(), rotation=45, horizontalalignment='right', fontsize=16)
    hm.set_yticklabels(hm.get_yticklabels(), rotation=0, horizontalalignment='right', fontsize=16)

    plt.title(title, fontsize=20)

    plt.xlabel(x_axis_name, fontsize=18)
    plt.ylabel(y_axis_name, fontsize=18)

    plt.tight_layout()

    save_path = save_path + "." + file_format

    plt.savefig(save_path, dpi=1200)
    plt.close()


def draw_heatmap_plotly(data: np.ndarray, labels_x: list, labels_y: list, save_path: str, x_axis_name: str, y_axis_name: str, title: str, fmt: str = ".2f", **kwargs):
    data = np.array(data, dtype=np.float32)

    # Color Scale
    if "reverse" in kwargs and kwargs["reverse"]:
        cs = "Viridis_r"
    else:
        cs = "Viridis"

    # Min-Max values
    zmax = 1.
    zmin = 0.

    if "auto_scale" in kwargs and kwargs["auto_scale"]:
        if None in data:
            zmax = max(
                max([data[i, j] for j in range(data.shape[1]) if data[i, j] is not None]) for i in range(data.shape[1]))
            zmin = min(
                min([data[i, j] for j in range(data.shape[1]) if data[i, j] is not None]) for i in range(data.shape[1]))
        else:
            zmax = np.max(data)
            zmin = np.min(data)

    data = np.array(data, dtype=np.float32)

    # Identity must be None if it is squared
    if data.shape[0] == data.shape[1]:
        for i in range(data.shape[0]):
            data[i, i] = None

    # Generate annotation
    annotation = []

    for i in range(data.shape[0]):
        annotation.append([])
        for j in range(data.shape[1]):
            if data[i, j] is not None:
                annotation[i].append(("{:" + fmt + "}").format(data[i, j]))
            else:
                annotation[i].append("")

    # Draw
    fig = ff.create_annotated_heatmap(z=data, x=labels_x, y=labels_y, zmax=zmax, zmin=zmin, showscale=True, hoverongaps=True, annotation_text=np.array(annotation), colorscale=cs)
    fig.update_layout(title_text=f"<b>{title}</b>", xaxis={"title": f"<b>{x_axis_name}</b>"}, yaxis={"title": f"<b>{y_axis_name}</b>"})

    save_path = save_path + ".html"

    plotly.offline.plot(fig, filename=save_path, auto_open=False)


def draw_heatmap(data: Union[List[List[float]] | np.ndarray], labels_x: List[str], labels_y: List[str], save_path: str, x_axis_name: str, y_axis_name: str, fmt: str = ".2f", **kwargs):
    """
        This method draws a heatmap

    :param data: Data
    :param labels_x: List of x-axis labels
    :param labels_y: List of y-axis labels
    :param save_path: Save path
    :param x_axis_name: Label for x-axis
    :param y_axis_name: Label for y-axis
    :param fmt: Annotation format
    :param kwargs: Additional arguments
    :return: Nothing
    """
    words = save_path.split("/")[-1].split(".")[0].split("_")

    for i in range(len(words)):
        words[i] = words[i].capitalize()

    title = " ".join(words)

    if isinstance(data, list):
        data = np.array(data, dtype=np.float32)

    if DRAWING_FORMAT == "plotly":
        draw_heatmap_plotly(data, labels_x, labels_y, save_path, x_axis_name, y_axis_name, title, fmt, **kwargs)
    elif DRAWING_FORMAT == "matplotlib-SVG":
        draw_heatmap_matplotlib(data, labels_x, labels_y, save_path, x_axis_name, y_axis_name, title, fmt, "svg", **kwargs)
    elif DRAWING_FORMAT == "matplotlib-PNG":
        draw_heatmap_matplotlib(data, labels_x, labels_y, save_path, x_axis_name, y_axis_name, title, fmt, "png",
                                **kwargs)
    else:
        raise Exception(f"Unknown drawing format: {DRAWING_FORMAT}")

    if "save_to_csv" not in kwargs or kwargs["save_to_csv"]:
        save_heatmap(data, labels_x, labels_y, save_path, x_axis_name, y_axis_name, title)


def save_heatmap(data: np.ndarray, labels_x: list, labels_y: list, save_path: str, x_axis_name: str, y_axis_name: str, title: str):
    save_path = save_path + ".csv"

    with open(save_path, "w") as f:
        f.write(title + ";\n\n")

        f.write(";" + x_axis_name + ";\n" + y_axis_name + ";")

        for j in range(len(labels_x)):
            f.write(str(labels_x[j]) + ";")

        f.write("\n")

        for i in range(data.shape[0]):
            f.write(str(labels_y[i]) + ";")

            for j in range(data.shape[1]):
                if data[i][j] is not None:
                    f.write(str(data[i][j]) + ";")
                else:
                    f.write(";")

            f.write("\n")


def draw_line_matplotlib(data: dict, save_path: str, x_axis_name: str, y_axis_name: str, title: str, file_format: str = "png"):
    # Plot them separately
    for key in data.keys():
        plt.plot(np.array(list(range(len(data[key])))), np.array(data[key]), label=key)

    plt.title(title, fontsize=20)
    plt.xlabel(x_axis_name, fontsize=18)
    plt.ylabel(y_axis_name, fontsize=18)

    plt.legend()

    fig = plt.gcf()
    fig.set_size_inches(18.5, 10.5)

    plt.tight_layout()

    save_path = save_path + "." + file_format

    plt.savefig(save_path, dpi=1200)
    plt.close()


def draw_line_plotly(data: dict, save_path: str, x_axis_name: str, y_axis_name: str, title: str):
    df = pd.DataFrame(data)

    fig = px.line(df, x=x_axis_name, y=y_axis_name, title=title)

    save_path = save_path + ".html"

    plotly.offline.plot(fig, filename=save_path, auto_open=False)


def draw_line(data: Dict[str, Union[List[float], np.ndarray]], save_path: str, x_axis_name: str, y_axis_name: str, save_to_csv: bool = True):
    """
        This method draws a line graph

    :param data: Corresponding label-data dictionary
    :param save_path: File path to save
    :param x_axis_name: Label for x-axis
    :param y_axis_name: Label for y-axis
    :param save_to_csv: Whether save as a csv, or not
    :return: Nothing
    """
    words = save_path.split("/")[-1].split(".")[0].split("_")

    for i in range(len(words)):
        words[i] = words[i].capitalize()

    title = " ".join(words)

    if DRAWING_FORMAT == "plotly":
        draw_line_plotly(data, save_path, x_axis_name, y_axis_name, title)
    elif DRAWING_FORMAT == "matplotlib-SVG":
        draw_line_matplotlib(data, save_path, x_axis_name, y_axis_name, title, "svg")
    elif DRAWING_FORMAT == "matplotlib-PNG":
        draw_line_matplotlib(data, save_path, x_axis_name, y_axis_name, title, "png")
    else:
        raise Exception(f"Unknown drawing format: {DRAWING_FORMAT}")

    if save_to_csv:
        save_line(data, save_path, x_axis_name, y_axis_name, title)


def save_line(data: dict, save_path: str, x_axis_name: str, y_axis_name: str, title: str):
    save_path = save_path + ".csv"

    with open(save_path, "w") as f:
        max_length = max([len(values) for values in data.values()])

        f.write(title + ";\n\n")

        f.write(x_axis_name + ";" + y_axis_name + ";\n" + x_axis_name + ";")

        key_list = list(data.keys())

        for key in key_list:
            f.write(str(key) + ";")

        f.write("\n")

        for i in range(max_length):
            f.write(str(i) + ";")

            for key in key_list:
                if len(data[key]) <= i:
                    f.write(";")
                else:
                    f.write(str(data[key][i]) + ";")

            f.write("\n")
