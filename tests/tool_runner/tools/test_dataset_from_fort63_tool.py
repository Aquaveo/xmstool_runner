"""Test datasets from "fort.63" tool."""
# 1. Standard python modules
import os

# 2. Third party modules
import pytest

# 3. Aquaveo modules

# 4. Local modules
from tests.compare_datasets import assert_dataset_files_equal
from xms.tool_runner.tools.dataset_from_fort63_tool import DatasetFromFort63Tool


class TestDatasetsFromFort63Tool:
    """Test class for DatasetFromFort63Tool."""

    @pytest.fixture
    def tool(self):
        """Return a DatasetFromFort63Tool."""
        yield DatasetFromFort63Tool()

    def test_run_tool(self, test_files_path: str, tool: DatasetFromFort63Tool):
        """Test running the tool."""
        # set up the tool
        test_files = os.path.join(test_files_path, 'adcirc_tools', 'dataset_from_fort63_tool', '')
        tool.set_gui_data_folder(test_files)
        tool.echo_output = False
        # set up the arguments
        arguments = tool.initial_arguments()
        input_file = os.path.join(test_files, 'fort.63.nc')
        arguments[DatasetFromFort63Tool.ARG_INPUT_GRID].value = 'ugrid'
        arguments[DatasetFromFort63Tool.ARG_INPUT_FILE].value = input_file
        arguments[DatasetFromFort63Tool.ARG_OUTPUT_DATASET].value = 'Dataset Name'

        tool.run_tool(arguments)

        # check tool output
        expected_output = (
            'Running tool "Dataset from fort.63.nc File"...\n'
            "Input parameters: {'input_ugrid': ugrid, 'fort_63_file': "
            f'{input_file}, '
            "'output_dataset': Dataset Name}\n"
            'Reading "Dataset Name" values from fort.63.nc.\n'
            'Writing the "Dataset Name" dataset values.\n'
            'Completed tool "Dataset from fort.63.nc File"\n')
        assert expected_output == tool.get_testing_output()

        # check output datasets
        dataset_name = 'Dataset Name'
        dataset_base = os.path.join(test_files, 'dataset_base', f'{dataset_name}.h5')
        dataset_out = os.path.join(test_files, 'grids', 'ugrid', f'{dataset_name}.h5')
        assert_dataset_files_equal(dataset_base, dataset_out)
