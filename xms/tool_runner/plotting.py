"""Plotting functions."""
from collections import namedtuple
from typing import Optional

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
import matplotlib.pyplot as pyplot
import matplotlib.tri as tri
import numpy
from PySide6 import QtCore
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QComboBox, QDialog, QDialogButtonBox, QLabel, QMainWindow, QVBoxLayout, QWidget)

from xms.constraint.ugrid_activity import active_cells_from_points, CellToPointActivityCalculator
from xms.datasets.dataset_reader import DatasetReader
from xms.grid.ugrid import UGrid
from xms.tool_core import DataHandler

PlotInfo = namedtuple('PlotInfo', ['dataset', 'time_step', 'color_map'])


def show_dataset_plot(data_handler: DataHandler, dataset_path: str, time_step: int, color_map: str = 'cool'):
    """Show a plot of a dataset in jupyter notebook.

    Args:
        data_handler: The data handler.
        dataset_path: Path to the dataset starting with the project data folder.
        time_step: The dataset timestep index.
        color_map: Color map to use.
    """
    _get_dataset_plot(data_handler, dataset_path, time_step, pyplot.figure(), color_map)


def get_dataset_plot(data_handler: DataHandler, dataset_path: str, time_step: int, color_map: str = 'cool'):
    """Get a plot of a dataset to be used by panel.

    Args:
        data_handler: The data handler.
        dataset_path: Path to the dataset starting with the project data folder.
        time_step: The dataset timestep index.
        color_map: Color map to use.
    """
    figure = Figure(tight_layout=True)
    return _get_dataset_plot(data_handler, dataset_path, time_step, figure, color_map)


def write_vtk_file(data_handler: DataHandler, dataset_path: str, time_step: int):
    """Write VTK file for dataset.

    Args:
        data_handler: The data handler.
        dataset_path: Path to the dataset starting with the project data folder.
        time_step: The dataset timestep index.
    """
    dataset_name, dataset, ugrid = _load_dataset(data_handler, dataset_path)
    point_values, hidden_cells, _ = _read_dataset_values(dataset, ugrid, time_step)
    x, y, triangles, masked = _get_contour_triangles(ugrid, hidden_cells)
    header = ('# vtk DataFile Version 4.0\n'
              'vtk output\n'
              'ASCII\n'
              'DATASET POLYDATA\n')
    with open(f'{dataset_path}_{time_step}.vtk', 'w') as f:
        f.write(header)
        f.write(f'POINTS {len(point_values)} double\n')
        for i in range(len(x)):
            f.write(f'{x[i]} {y[i]} 0.0\n')
        visible_tri_count = len(masked) - numpy.count_nonzero(masked)
        f.write(f'POLYGONS {visible_tri_count} {visible_tri_count * 4}\n')
        for i in range(len(triangles)):
            if not masked[i]:
                t = triangles[i]
                f.write(f'3 {t[0]} {t[1]} {t[2]}\n')
        f.write(f'\nPOINT_DATA {len(point_values)}\n')
        f.write('SCALARS point_values double 1\n')
        f.write('LOOKUP_TABLE default\n')
        for value in point_values:
            f.write(f'{value}\n')


def _get_dataset_plot(data_handler, dataset_path, time_step, figure, color_map):
    """Get a plot of a dataset.

    Args:
        data_handler: The data handler.
        dataset_path: Path to the dataset starting with the project data folder.
        time_step: The dataset timestep index.
        figure: The figure to plot the dataset into.
        color_map: The colormap to use.
    """
    dataset_name, dataset, ugrid = _load_dataset(data_handler, dataset_path)
    point_values, hidden_cells, range = _read_dataset_values(dataset, ugrid, time_step)
    x, y, triangles, mask = _get_contour_triangles(ugrid, hidden_cells)
    return _contour_plot(figure, dataset_name, x, y, point_values, triangles, mask, color_map, range)


def _load_dataset(data_handler: DataHandler, dataset_path: str):
    """Load the dataset.

    Args:
        data_handler: The data handler.
        dataset_path: Path to the dataset starting with the project folder.

    Returns:
        A tuple containing the dataset name, dataset, and UGrid.
    """
    dataset = data_handler.get_input_dataset(dataset_path)
    co_grid = data_handler.get_input_dataset_grid(dataset_path)
    if co_grid is None:
        raise FileNotFoundError("Unable to read the dataset's grid.")
    ugrid = co_grid.ugrid
    return dataset_path, dataset, ugrid


def _read_dataset_values(dataset: DatasetReader, ugrid: UGrid, time_step: int):
    """Read the dataset values.

    Args:
        dataset: The dataset reader.
        ugrid: The dataset's UGrid.
        time_step: The time step index.

    Returns:
        A tuple containing the point values and hidden cells.
    """
    if dataset.activity is not None and dataset.values.shape != dataset.activity.shape:
        dataset.activity_calculator = CellToPointActivityCalculator(ugrid)
    overall_min = float('inf')
    overall_max = float('-inf')
    for step_idx in range(dataset.num_times):
        point_values, activity = dataset.timestep_with_activity(step_idx, nan_activity=True)
        overall_min = min((overall_min, numpy.nanmin(point_values)))
        overall_max = max((overall_max, numpy.nanmax(point_values)))
    point_values, activity = dataset.timestep_with_activity(time_step, nan_activity=True)
    if activity is None or activity.shape == point_values.shape:
        activity = active_cells_from_points(ugrid, ~numpy.isnan(point_values))
    hidden_cells = activity == 0
    min_value = numpy.nanmin(point_values)
    point_values[numpy.isnan(point_values)] = min_value
    return point_values, hidden_cells, (overall_min, overall_max)


def _get_contour_triangles(ugrid, hidden_cells):
    """Load contour info for plotting.

    Args:
        ugrid: The UGrid.
        hidden_cells: The hidden cells.

    Returns:
        A tuple containing the x locations, y locations, triangles, and hidden mask.
    """
    locations = numpy.array(ugrid.locations)
    x = locations[:, 0]
    y = locations[:, 1]

    triangles = []
    grid_indices = []
    for cell_index in range(ugrid.cell_count):
        cell_points = ugrid.get_cell_points(cell_index)
        cell_point_count = len(cell_points)
        if cell_point_count == 3:
            pt0 = cell_points[0]
            pt1 = cell_points[1]
            pt2 = cell_points[2]
            triangles.append([pt0, pt1, pt2])
            grid_indices.append(cell_index)
        elif cell_point_count == 4:
            pt0 = cell_points[0]
            pt1 = cell_points[1]
            pt2 = cell_points[2]
            pt3 = cell_points[3]
            triangles.append([pt0, pt1, pt2])
            triangles.append([pt2, pt3, pt0])
            grid_indices.extend((cell_index, cell_index))
    triangles = numpy.array(triangles)
    mask = [hidden_cells[grid_indices[tri_index]] for tri_index in range(len(grid_indices))]
    mask = numpy.array(mask)
    return x, y, triangles, mask


def _contour_plot(figure, title, x, y, point_values, triangles, mask, color_map, range):
    """Get a contour plot of the values.

    Args:
        figure: The figure to show the plot in.
        title: The title of the plot.
        x: The X point locations.
        y: The Y point locations.
        point_values: The values at the points.
        triangles: The triangles.
        mask: Mask for the hidden triangles.
        color_map: Color map to use.
        range: The range to show the contour plot.

    Returns:
        A contour plot of the values.
    """
    triangulation = tri.Triangulation(x, y, triangles=triangles, mask=mask)
    axes = figure.subplots()
    axes.set_aspect('equal')
    min_range, max_range = range
    if min_range == max_range:
        min_range -= 10
        max_range += 10
    num_levels = 11
    levels = numpy.linspace(min_range, max_range, num_levels)
    tri_contour_set = axes.tricontourf(triangulation, point_values, levels=levels, cmap=color_map)
    figure.colorbar(tri_contour_set)
    axes.set_title(title)
    axes.set_xlabel('X location')
    axes.set_ylabel('Y location')
    return figure


class PlotCanvas(FigureCanvas):
    """Plotting canvas for displaying dataset."""

    def __init__(self, data_handler: DataHandler, dataset_path: str, time_step: int, color_map: str):
        """
        Initialize the object.

        Args:
            data_handler: The data handler.
            dataset_path: The path to the dataset.
            time_step: The dataset time step.
            color_map: Color map to use.
        """
        fig = get_dataset_plot(data_handler, dataset_path, time_step, color_map)
        super().__init__(fig)


class DatasetPlotWindow(QMainWindow):
    """Application window showing dataset plot."""

    def __init__(self, data_handler: DataHandler, dataset_path: str, time_step: int, color_map: str):
        """
        Initialize the object.

        Args:
            data_handler: The data handler.
            dataset_path: The path to the dataset.
            time_step: The dataset time step.
            color_map: Color map to use.
        """
        super().__init__(parent=None, flags=Qt.WindowType.Dialog)
        self.setWindowTitle(dataset_path)
        self.main_widget = QWidget(self)
        self.setCentralWidget(self.main_widget)

        layout = QVBoxLayout(self.main_widget)
        canvas = PlotCanvas(data_handler, dataset_path, time_step, color_map)
        layout.addWidget(canvas)
        self.addToolBar(QtCore.Qt.BottomToolBarArea, NavigationToolbar(canvas, self))
        self.main_widget.setFocus()


class DatasetPlotInfo(QDialog):
    """Application window showing a plot of the dataset."""
    def __init__(self, data_handler: DataHandler, color_map: str, parent: Optional[QWidget] = None):
        """
        Initializes an instance of the class.

        Args:
            data_handler: The data handler.
            color_map: The default name of the color map to use.
            parent: The parent widget. Defaults to None.
        """
        super().__init__(parent)
        self._data_handler = data_handler
        self.last_dataset = None

        self.setWindowTitle("Plot Dataset")
        self.setWindowModality(QtCore.Qt.ApplicationModal)

        # UI for selecting a dataset
        datasets = data_handler.get_available_datasets()
        self.dataset_combo = QComboBox()
        self.dataset_combo.addItems(datasets)
        self.dataset_combo.setPlaceholderText("Select a dataset")
        self.dataset_combo.setCurrentIndex(-1)
        self.dataset_combo.currentTextChanged.connect(self._combo_changed)

        # UI for entering a time step
        self.time_step_combo = QComboBox()
        self.time_step_combo.setPlaceholderText("Select a time step")
        self.time_step_combo.setCurrentIndex(-1)
        self.time_step_combo.currentTextChanged.connect(self._combo_changed)

        # UI for selecting a color map
        color_maps: list[str] = pyplot.colormaps()
        color_maps = sorted(color_maps, key=str.lower)
        self.color_map_combo = QComboBox()
        self.color_map_combo.setPlaceholderText("Select a color map")
        self.color_map_combo.addItems(color_maps)
        self.color_map_combo.setCurrentText(color_map)
        self.color_map_combo.currentTextChanged.connect(self._combo_changed)

        # UI for viewing matplotlib documentation for color maps
        self.color_map_link = QLabel(self)
        color_map_link = ('<a href="https://matplotlib.org/stable/gallery/color/colormap_reference.html">'
                          'matplotlib color maps</a>')
        self.color_map_link.setText(color_map_link)
        self.color_map_link.setOpenExternalLinks(True)

        # UI for OK/Cancel buttons
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.button_box.button(QDialogButtonBox.Ok).setEnabled(False)

        layout = QVBoxLayout()
        layout.addWidget(self.dataset_combo)
        layout.addWidget(self.time_step_combo)
        layout.addWidget(self.color_map_combo)
        layout.addWidget(self.color_map_link)
        layout.addWidget(self.button_box)
        self.setLayout(layout)

    def _combo_changed(self, _: int):
        """React to change in combo box values."""
        # Update time steps
        current_dataset = self.dataset_combo.currentText()
        current_time_step = self.time_step_combo.currentText()
        if current_dataset != self.last_dataset:
            dataset = self._data_handler.get_input_dataset(current_dataset)
            if dataset is not None:
                time_steps = [str(time_step + 1) for time_step in range(dataset.num_times)]
            else:
                time_steps = ["1"]
            self.time_step_combo.addItems(time_steps)
            if current_time_step in time_steps:
                self.time_step_combo.setCurrentText(current_time_step)
            self.last_dataset = current_dataset
        dataset_index = self.dataset_combo.currentIndex()
        time_step_index = self.time_step_combo.currentIndex()
        color_map_index = self.color_map_combo.currentIndex()
        ok_enabled = dataset_index >= 0 and time_step_index >= 0 and color_map_index >= 0
        self.button_box.button(QDialogButtonBox.Ok).setEnabled(ok_enabled)


def get_dataset_plot_info(data_handler: DataHandler, color_map: str) -> Optional[PlotInfo]:
    """
    Get info for plotting a dataset.

    Args:
        data_handler: The project data handler.
        color_map: The default color map to use.

    Returns:
        Tuple with the dataset path, time step, and matplotlib color map.
    """
    dataset_plot_info = DatasetPlotInfo(data_handler, color_map)
    if dataset_plot_info.exec_():
        dataset = dataset_plot_info.dataset_combo.currentText()
        time_step = int(dataset_plot_info.time_step_combo.currentText()) - 1
        color_map = dataset_plot_info.color_map_combo.currentText()
        return PlotInfo(dataset, time_step, color_map)
    return None
