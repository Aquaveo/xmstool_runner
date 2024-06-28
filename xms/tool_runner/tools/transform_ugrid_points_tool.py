"""Tool to transform Ugrid points."""

# 1. Standard python modules
from pathlib import Path
import subprocess

# 2. Third party modules
import numpy as np

# 3. Aquaveo modules
from xms.constraint import UnconstrainedGrid
from xms.core.filesystem import filesystem
from xms.grid.ugrid import UGrid
from xms.tool_core import Argument, IoDirection, Tool

# 4. Local modules


__copyright__ = "(C) Aquaveo 2024"
__license__ = "All rights reserved"


class TransformUgridPointsTool(Tool):
    """Tool to transform Ugrid points between projections."""
    ARG_INPUT_GRID = 0
    ARG_GDAL_TOOLS_PATH = 1
    ARG_EPSG_CODE_FROM = 2
    ARG_EPSG_CODE_TO = 3
    ARG_OUTPUT_GRID = 4

    def __init__(self):
        """Initialize the tool."""
        super().__init__(name="Transform UGrid Points")

    def initial_arguments(self) -> list[Argument]:
        """Create the tool arguments.

        Returns:
            A list of the tool arguments.
        """
        arguments = [
            self.grid_argument(name="input_grid", description="Input UGrid"),
            self.file_argument(name="gdal_tools_path", description="Path to GDAL command line tools",
                               select_folder=True, value="", optional=True),
            self.integer_argument(name="epsg_code_from", description="EPSG code from"),
            self.integer_argument(name="epsg_code_to", description="EPSG code to"),
            self.grid_argument(name="output_grid", description="Output UGrid", io_direction=IoDirection.OUTPUT)
        ]
        return arguments

    def run(self, arguments: list[Argument]) -> None:
        """Override to run the tool.

        Args:
            arguments (list): The tool arguments.
        """
        # get the input values
        input_grid = arguments[self.ARG_INPUT_GRID].text_value
        gdal_tools_path = arguments[self.ARG_GDAL_TOOLS_PATH].text_value
        epsg_code_from = arguments[self.ARG_EPSG_CODE_FROM].value
        epsg_code_to = arguments[self.ARG_EPSG_CODE_TO].value
        co_grid_in = self.get_input_grid(input_grid)
        ugrid_in = co_grid_in.ugrid
        locations_in = np.array(ugrid_in.locations)

        # get the new grid point locations and WKT
        locations_out = self._transform_points(gdal_tools_path, locations_in, epsg_code_from, epsg_code_to)
        wkt = self._wkt_from_epsg(gdal_tools_path, epsg_code_to)

        # build and set the output grid
        ugrid_out = UGrid(locations_out, ugrid_in.cellstream)
        co_grid_out = UnconstrainedGrid(ugrid_out)
        self.set_output_grid(co_grid_out, arguments[self.ARG_OUTPUT_GRID], wkt)

    def _transform_points(self, gdal_tools_path: str,
                          locations_in: np.ndarray,
                          epsg_code_from: int,
                          epsg_code_to: int) -> np.ndarray:
        """Run gdaltransform tool to transform a list of points between two EPSG codes.

        Args:
            gdal_tools_path: The path to the GDAL tools.
            locations_in: The locations to transform.
            epsg_code_from: The EPSG code to transform from.
            epsg_code_to: The EPSG code to transform to.

        Returns:
            The transformed points.
        """
        self.logger.info("Running gdaltransform to transform the locations.")
        # write the input points to a temporary file
        temp_point_file_in = filesystem.temp_filename()
        np.savetxt(temp_point_file_in, locations_in, fmt='%d')

        # run the command with stdin redirected from the input point file
        # and stdout redirected to the output point file
        temp_point_file_out = filesystem.temp_filename()
        try:
            transform_command = _get_command_path(gdal_tools_path, "gdaltransform")
            arguments = [transform_command, "-s_srs", f"EPSG:{epsg_code_from}", "-t_srs", f"EPSG:{epsg_code_to}"]
            with open(temp_point_file_in, "r") as point_file_in, open(temp_point_file_out, "w") as point_file_out:
                subprocess.run(arguments, stdin=point_file_in, stdout=point_file_out, stderr=subprocess.PIPE,
                               check=True)
        except subprocess.CalledProcessError as e:
            error = f"Unable to run gdaltransform: {str(e)}"
            self.fail(error)

        # read the transformed points from the output file
        transformed_points = np.loadtxt(temp_point_file_out)
        return transformed_points

    def _wkt_from_epsg(self, gdal_tools_path: str, epsg_code: int) -> str | None:
        """Call gdalsrsinfo tool to get the WKT for an EPSG code.

        Args:
            gdal_tools_path: The path to the GDAL tools.
            epsg_code: The EPSG code.

        Returns:
            The WKT for the EPSG code.
        """
        self.logger.info("Running gdalsrsinfo to retrieve the new projection's WKT.")
        wkt = None
        try:
            gdal_srs_info_command = _get_command_path(gdal_tools_path, "gdalsrsinfo")
            arguments = [gdal_srs_info_command, "-o", "wkt", f"EPSG:{epsg_code}"]
            result = subprocess.run(arguments, capture_output=True, check=True)
            wkt = result.stdout
        except subprocess.CalledProcessError as e:
            error = f"Unable to retrieve WKT for EPSG code: {str(e)}"
            self.fail(error)
        return wkt


def _get_command_path(gdal_tools_path: str, command: str):
    """Get the full command path.

    Args:
        gdal_tools_path: The path to the GDAL tools if provided.
        command: The command to be executed.

    Returns:
        str: The full path to the command, including the GDAL tools path if provided.
    """
    if gdal_tools_path:
        transform_path = Path(gdal_tools_path) / command
        transform_command = str(transform_path.as_posix())
    else:
        transform_command = command
    return transform_command
