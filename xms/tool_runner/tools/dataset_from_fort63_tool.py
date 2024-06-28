"""Tool to create a UGrid from "fort.63" file."""
# 1. Standard python modules

# 2. Third party modules

# 3. Aquaveo modules
from xms.tool_core import Argument, IoDirection, Tool

# 4. Local modules
from xms.adcirc import Fort63Reader

__copyright__ = "(C) Aquaveo 2024"
__license__ = "All rights reserved"


class DatasetFromFort63Tool(Tool):
    """Tool to create a dataset from a "fort.63" file."""
    ARG_INPUT_GRID = 0
    ARG_INPUT_FILE = 1
    ARG_OUTPUT_DATASET = 2

    def __init__(self):
        """Constructor."""
        super().__init__(name='Dataset from fort.63.nc File')

    def initial_arguments(self) -> list[Argument]:
        """Get initial arguments for tool.

        Must override.

        Returns:
            (list): A list of the initial tool arguments.
        """
        arguments = [
            self.grid_argument(name='input_ugrid', description='Input UGrid'),
            self.file_argument(name='fort_63_file', description='Input fort.63.nc file'),
            self.dataset_argument(name='output_dataset', description='Output dataset', value='Water Surface (eta)',
                                  io_direction=IoDirection.OUTPUT)
        ]
        return arguments

    def run(self, arguments: list[Argument]) -> None:
        """Override to run the tool.

        Args:
            arguments (list): The tool arguments.
        """
        # get the input file path
        fort_63_file = arguments[self.ARG_INPUT_FILE].text_value
        dataset_name = arguments[self.ARG_OUTPUT_DATASET].text_value

        # read and create the datasets with the fort.63 reader
        geom_uuid, geom_num_nodes = self.get_grid_info(arguments[self.ARG_INPUT_GRID])
        fort_63_reader = Fort63Reader(fort_63_file, dataset_name, geom_uuid, geom_num_nodes,
                                      logger=self.logger)
        fort_63_reader.read()

        # set the output dataset
        dataset = fort_63_reader.dataset_writer
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
