"""ExportProjectTool class."""
# 1. Standard python modules

# 2. Third party modules

# 3. Aquaveo modules
from xms.tool_core import Argument, IoDirection, Tool

# 4. Local modules
from xms.tool_runner.tools.export_project import export_project

__copyright__ = "(C) Copyright Aquaveo 2022"
__license__ = "All rights reserved"


class ExportProjectTool(Tool):
    """Tool to export a project to a folder for use by tools."""
    ARG_INPUT_PROJECT = 0
    ARG_OUTPUT_FOLDER = 1

    def __init__(self):
        """Initializes the class."""
        super().__init__(name='ExportProjectTool')

    def initial_arguments(self) -> list[Argument]:
        """Get initial arguments for tool.

        Must override.

        Returns:
            A list of the initial tool arguments.
        """
        arguments = [
            self.file_argument(name='input_file', description='Project file to process'),
        ]
        return arguments

    def run(self, arguments):
        """Run the tool.

        Args:
            arguments (list): The tool arguments.
        """
        input_file = arguments[self.ARG_INPUT_PROJECT].value
        output_folder = self.project_folder
        export_project(input_file, output_folder, self.logger)


__all__ = ['ExportProjectTool']
