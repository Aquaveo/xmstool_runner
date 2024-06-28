"""Tests for UGridFromFort14Tool."""

# 1. Standard python modules
import filecmp
import os

# 2. Third party modules
import pytest

# 3. Aquaveo modules

# 4. Local modules
from xms.tool_runner.tools.ugrid_from_fort14_tool import UGridFromFort14Tool


__copyright__ = "(C) Aquaveo 2024"
__license__ = "All rights reserved"


class TestUGridFromFort14Tool:
    """Test class for UGridFromFort14Tool."""

    @pytest.fixture
    def tool(self) -> UGridFromFort14Tool:
        """
        Returns an instance of the UGridFromFort14Tool class.

        Returns:
            An instance of the UGridFromFort14Tool class.
        """
        yield UGridFromFort14Tool()

    def test_run_tool(self, tool, test_files_path):
        """Test running the tool."""
        test_files = os.path.join(test_files_path, 'adcirc_tools', 'ugrid_from_fort14_tool')
        tool.set_gui_data_folder(test_files)
        tool.echo_output = False
        arguments = tool.initial_arguments()
        input_file = os.path.join(test_files, 'fort.14')
        arguments[UGridFromFort14Tool.ARG_INPUT_FILE].value = input_file
        arguments[UGridFromFort14Tool.ARG_OUTPUT_UGRID].value = 'ugrid_out'
        tool.run_tool(arguments)
        expected_output = (
            'Running tool "UGrid from fort.14 File"...\n'
            "Input parameters: {'fort_14_file': "
            f'{input_file}, '
            "'ugrid_name': ugrid_out}\n"
            'Loading fort.14 from ASCII file...\n'
            'Parsing mesh node locations...\n'
            'Parsing mesh element definitions...\n'
            'Building the UGrid...\n'
            f'Successfully read "{input_file}".\n'
            'Completed tool "UGrid from fort.14 File"\n')
        assert expected_output == tool.get_testing_output()
        output_file = os.path.join(test_files, 'grids', 'ugrid_out.xmc')
        base_file = os.path.join(test_files, 'ugrid_base.xmc')
        assert filecmp.cmp(output_file, base_file, shallow=False)
