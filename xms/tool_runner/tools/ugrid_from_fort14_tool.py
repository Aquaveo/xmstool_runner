"""Tool to create a UGrid from "fort.14" file."""
# 1. Standard python modules

# 2. Third party modules

# 3. Aquaveo modules
from xms.tool_core import Argument, IoDirection, Tool

# 4. Local modules
from xms.adcirc import Fort14Reader

__copyright__ = "(C) Aquaveo 2024"
__license__ = "All rights reserved"


class UGridFromFort14Tool(Tool):
    """Tool to create a UGrid from a "fort.14" file."""
    ARG_INPUT_FILE = 0
    ARG_OUTPUT_UGRID = 1

    def __init__(self):
        """Constructor."""
        super().__init__(name='UGrid from fort.14 File')

    def initial_arguments(self) -> list[Argument]:
        """Get initial arguments for tool.

        Must override.

        Returns:
            (list): A list of the initial tool arguments.
        """
        arguments = [
            self.file_argument(name='fort_14_file', description='Input fort.14 file'),
            self.grid_argument(name='ugrid_name', description='Name of the output UGrid',
                               io_direction=IoDirection.OUTPUT)
        ]
        return arguments

    def run(self, arguments: list[Argument]) -> None:
        """Override to run the tool.

        Args:
            arguments (list): The tool arguments.
        """
        # get the input fort.14 file
        fort_14_file = arguments[self.ARG_INPUT_FILE].text_value
        # read the UGrid and WKT
        fort_14_reader = Fort14Reader(fort_14_file, logger=self.logger)
        co_grid, wkt = fort_14_reader.read()
        # set the output grid
        self.set_output_grid(co_grid, arguments[self.ARG_OUTPUT_UGRID], projection=wkt)
