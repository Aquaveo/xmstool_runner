"""Tool to create a UGrid from "fort.13" file."""
# 1. Standard python modules

# 2. Third party modules

# 3. Aquaveo modules
from xms.tool_core import Argument, Tool

# 4. Local modules
from xms.adcirc import Fort13Reader

__copyright__ = "(C) Aquaveo 2024"
__license__ = "All rights reserved"


class DatasetsFromFort13Tool(Tool):
    """Tool to create datasets from a "fort.13" file."""
    ARG_INPUT_GRID = 0
    ARG_INPUT_FILE = 1

    def __init__(self):
        """Constructor."""
        super().__init__(name='Datasets from fort.13 File')

    def initial_arguments(self) -> list[Argument]:
        """Get initial arguments for tool.

        Must override.

        Returns:
            (list): A list of the initial tool arguments.
        """
        arguments = [
            self.grid_argument(name='input_ugrid', description='Input UGrid'),
            self.file_argument(name='fort_13_file', description='Input fort.13 file')
        ]
        return arguments

    def run(self, arguments: list[Argument]) -> None:
        """Override to run the tool.

        Args:
            arguments (list): The tool arguments.
        """
        # get the input file path
        fort_13_file = arguments[self.ARG_INPUT_FILE].text_value

        # read and create the datasets with the fort.13 reader
        geom_uuid, geom_num_nodes = self.get_grid_info(arguments[self.ARG_INPUT_GRID])
        fort_13_reader = Fort13Reader(fort_13_file, geom_uuid, geom_num_nodes, logger=self.logger)
        fort_13_reader.read()

        # set the output datasets
        datasets = fort_13_reader.datasets
        for _, dataset in datasets.items():
            self.set_output_dataset(dataset)

    def get_grid_info(self, grid_argument: Argument) -> tuple[str, int]:
        """Get the UUID and number of points for the input grid.

        Args:
            grid_argument: The input grid argument.

        Returns:
            The UUID and number of points for the input grid.
        """
        co_grid = self.get_input_grid(grid_argument.text_value)
        return co_grid.uuid, co_grid.ugrid.point_count
