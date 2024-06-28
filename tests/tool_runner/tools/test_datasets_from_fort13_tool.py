"""Test datasets from "fort.13" tool."""
# 1. Standard python modules
import os

# 2. Third party modules
import pytest

# 3. Aquaveo modules

# 4. Local modules
from tests.compare_datasets import assert_dataset_files_equal
from xms.tool_runner.tools.datasets_from_fort13_tool import DatasetsFromFort13Tool


class TestDatasetsFromFort13Tool:
    """Test class for DatasetsFromFort13Tool."""

    @pytest.fixture
    def tool(self):
        """Return a DatasetsFromFort13Tool."""
        yield DatasetsFromFort13Tool()

    def test_run_tool(self, tool: DatasetsFromFort13Tool, test_files_path):
        """Test running the tool."""
        # set up the tool
        test_files = os.path.join(test_files_path, 'adcirc_tools', 'datasets_from_fort13_tool', '')
        tool.set_gui_data_folder(test_files)
        tool.echo_output = False
        # set up the arguments
        arguments = tool.initial_arguments()
        input_file = os.path.join(test_files, 'fort.13')
        arguments[DatasetsFromFort13Tool.ARG_INPUT_GRID].value = 'ugrid'
        arguments[DatasetsFromFort13Tool.ARG_INPUT_FILE].value = input_file

        tool.run_tool(arguments)

        # check tool output
        expected_output = (
            'Running tool "Datasets from fort.13 File"...\n'
            "Input parameters: {'input_ugrid': ugrid, "
            f"'fort_13_file': {input_file}"
            '}\n'
            'Reading nodal attribute properties...\n'
            'Reading value for nodal attribute: sea_surface_height_above_geoid (1 '
            'dataset)\n'
            'Reading value for nodal attribute: bottom_roughness_length (1 dataset)\n'
            'Creating dataset 1 of 1...\n'
            'Reading value for nodal attribute: bridge_pilings_friction_paramenters (4 '
            'datasets)\n'
            'Creating dataset 1 of 4...\n'
            'Creating dataset 2 of 4...\n'
            'Creating dataset 3 of 4...\n'
            'Creating dataset 4 of 4...\n'
            'Successfully read ADCIRC nodal attributes from '
            f'"{input_file}".\n'
            'Completed tool "Datasets from fort.13 File"\n')
        assert expected_output == tool.get_testing_output()

        # check output datasets
        datasets = ['BAlpha', 'BDelX', 'BK', 'POAN', 'Z0b_var']
        for dataset in datasets:
            dataset_base = os.path.join(test_files, 'datasets_base', f'{dataset}.h5')
            dataset_out = os.path.join(test_files, 'grids', 'ugrid', f'{dataset}.h5')
            assert_dataset_files_equal(dataset_base, dataset_out)
