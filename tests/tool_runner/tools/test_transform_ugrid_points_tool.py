"""Tests for TransformUgridPointsTool."""

# 1. Standard python modules
import filecmp
import os
import subprocess
from unittest import mock

# 2. Third party modules
import pytest

# 3. Aquaveo modules
from xms.tool_core import ToolError

# 4. Local modules
from xms.tool_runner.tools.transform_ugrid_points_tool import TransformUgridPointsTool


@pytest.fixture
def tool(test_files_path):
    """Fixture for TransformUgridPointsTool."""
    tool = TransformUgridPointsTool()
    tool.set_gui_data_folder(os.path.join(test_files_path, "transform_ugrid_points_tool"))
    tool.echo_output = False
    yield tool


class SubprocessRun:
    """Callable to mock "subprocess.run" for testing."""

    def __init__(self):
        """Constructor."""
        self.mock_values = {
            "gdaltransform": {
                "arguments": "",
                "stdin": None,
                "stdout": "",
                "stderr": "",
                "exit_code": 0,
                "failure": ""
            },
            "gdalsrsinfo": {
                "arguments": "",
                "stdin": None,
                "stdout": "",
                "stderr": "",
                "exit_code": 0,
                "failure": ""
            }
        }

    def __call__(self, arguments, *args, **kwargs):
        """Replacement for "subprocess.run" for testing.

        Args:
            arguments: The command line arguments to be passed to the gdaltransform tool.
            **kwargs: Additional keyword arguments including check, stdin, and stdout.
        """
        if "gdaltransform" in arguments[0]:
            return self._process_gdaltransform(arguments, **kwargs)
        elif "gdalsrsinfo" in arguments[0]:
            return self._process_gdalsrsinfo(arguments, **kwargs)

    def _process_gdaltransform(self, arguments, **kwargs):
        """Mock of running gdaltransform tool.

        Args:
            arguments: The command line arguments to be passed to the gdaltransform tool.
            **kwargs: Additional keyword arguments including stdin and stdout.
        """
        if self.mock_values["gdaltransform"]["failure"] and kwargs.pop("check"):
            raise subprocess.CalledProcessError(-1, arguments, self.mock_values["gdaltransform"]["failure"])

        self.mock_values["gdaltransform"]["arguments"] = arguments
        stdin = kwargs.pop("stdin")
        self.mock_values["gdaltransform"]["stdin"] = stdin.read()

        stdout = kwargs.pop("stdout")
        stdout.write(self.mock_values["gdaltransform"]["stdout"])

    def _process_gdalsrsinfo(self, arguments, **kwargs):
        """Mock of running gdalsrsinfo tool.

        Args:
            arguments: The arguments to be passed to the gdalsrsinfo command.
            **kwargs: Additional keyword arguments including check.

        Returns:
            A subprocess.CompletedProcess object that represents the result of running the gdalsrsinfo command.
            The object contains the following attributes:
            - args: The arguments passed to the command.
            - returncode: The exit code of the command.
            - stdout: The standard output of the command.
            - stderr: The standard error of the command.
        """
        if self.mock_values["gdalsrsinfo"]["failure"] and kwargs.pop("check"):
            raise subprocess.CalledProcessError(-1, arguments, self.mock_values["gdalsrsinfo"]["failure"])

        self.mock_values["gdalsrsinfo"]["arguments"] = arguments
        exit_code = self.mock_values["gdalsrsinfo"]["exit_code"]
        stdout = self.mock_values["gdalsrsinfo"]["stdout"]
        stderr = self.mock_values["gdalsrsinfo"]["stderr"]

        return subprocess.CompletedProcess(arguments, exit_code, stdout, stderr)


@mock.patch('xms.tool_runner.tools.transform_ugrid_points_tool.subprocess.run')
def test_run_tool(mock_subprocess_run, tool, test_files_path):
    """Test running the tool."""
    # mock subprocess.run for gdaltransform and gdalsrsinfo
    subprocess_run = SubprocessRun()
    subprocess_run.mock_values["gdaltransform"]["stdout"] = (
        "-111.6574963628 40.271514127177 10.0\n"
        "-111.656337674 40.273322561347 11.0\n"
        "-111.6539680392 40.271534121981 12.0\n"
    )
    subprocess_run.mock_values["gdalsrsinfo"]["stdout"] = "the WKT"
    mock_subprocess_run.side_effect = subprocess_run

    # set up the tool arguments
    arguments = tool.initial_arguments()
    arguments[tool.ARG_INPUT_GRID].value = "ugrid_in"
    arguments[tool.ARG_GDAL_TOOLS_PATH].value = ""
    arguments[tool.ARG_EPSG_CODE_FROM].value = 2956
    arguments[tool.ARG_EPSG_CODE_TO].value = 4979
    arguments[tool.ARG_OUTPUT_GRID].value = "ugrid_out"

    tool.run_tool(arguments)

    expected_output = (
        'Running tool "Transform UGrid Points"...\n'
        "Input parameters: {'input_grid': ugrid_in, 'gdal_tools_path': ,"
        " 'epsg_code_from': 2956, 'epsg_code_to': 4979, 'output_grid': "
        'ugrid_out}\n'
        'Running gdaltransform to transform the locations.\n'
        "Running gdalsrsinfo to retrieve the new projection's WKT.\n"
        'Completed tool "Transform UGrid Points"\n')
    assert expected_output == tool.get_testing_output()
    # check gdaltransform call
    expected_stdin = '444100 4458100 10\n444200 4458300 11\n444400 4458100 12\n'
    assert expected_stdin == subprocess_run.mock_values["gdaltransform"]["stdin"]
    expected_arguments = ['gdaltransform', '-s_srs', 'EPSG:2956', '-t_srs', 'EPSG:4979']
    assert expected_arguments == subprocess_run.mock_values["gdaltransform"]["arguments"]
    # check gdalsrcinfo call
    expected_arguments = ['gdalsrsinfo', '-o', 'wkt', 'EPSG:4979']
    assert expected_arguments == subprocess_run.mock_values["gdalsrsinfo"]["arguments"]
    assert "the WKT" == subprocess_run.mock_values["gdalsrsinfo"]["stdout"]
    # check the output grid
    base_file = os.path.join(test_files_path, "transform_ugrid_points_tool", "ugrid_base.xmc")
    out_file = os.path.join(test_files_path, "transform_ugrid_points_tool", "grids", "ugrid_out.xmc")
    assert filecmp.cmp(base_file, out_file, shallow=False)


@mock.patch('xms.tool_runner.tools.transform_ugrid_points_tool.subprocess.run')
def test_run_tool_with_path(mock_subprocess_run, tool, test_files_path):
    """Test running the tool with a path to GDAL."""
    # mock subprocess.run for gdaltransform and gdalsrsinfo
    subprocess_run = SubprocessRun()
    subprocess_run.mock_values["gdaltransform"]["stdout"] = (
        "-111.6574963628 40.271514127177 10.0\n"
        "-111.656337674 40.273322561347 11.0\n"
        "-111.6539680392 40.271534121981 12.0\n"
    )
    subprocess_run.mock_values["gdalsrsinfo"]["stdout"] = "the WKT"
    mock_subprocess_run.side_effect = subprocess_run

    # set up the tool arguments
    arguments = tool.initial_arguments()
    arguments[tool.ARG_INPUT_GRID].value = "ugrid_in"
    arguments[tool.ARG_GDAL_TOOLS_PATH].value = "C:/Program Files/GDAL"
    arguments[tool.ARG_EPSG_CODE_FROM].value = 2956
    arguments[tool.ARG_EPSG_CODE_TO].value = 4979
    arguments[tool.ARG_OUTPUT_GRID].value = "ugrid_out"

    tool.run_tool(arguments)

    expected_output = (
        'Running tool "Transform UGrid Points"...\n'
        "Input parameters: {'input_grid': ugrid_in, 'gdal_tools_path': C:/Program "
        "Files/GDAL, 'epsg_code_from': 2956, 'epsg_code_to': 4979, 'output_grid': "
        'ugrid_out}\n'
        'Running gdaltransform to transform the locations.\n'
        "Running gdalsrsinfo to retrieve the new projection's WKT.\n"
        'Completed tool "Transform UGrid Points"\n')
    assert expected_output == tool.get_testing_output()
    # check gdaltransform call
    expected_stdin = '444100 4458100 10\n444200 4458300 11\n444400 4458100 12\n'
    assert expected_stdin == subprocess_run.mock_values["gdaltransform"]["stdin"]
    expected_arguments = [
        'C:/Program Files/GDAL/gdaltransform',
        '-s_srs',
        'EPSG:2956',
        '-t_srs',
        'EPSG:4979']
    assert expected_arguments == subprocess_run.mock_values["gdaltransform"]["arguments"]
    # check gdalsrcinfo call
    expected_arguments = ['C:/Program Files/GDAL/gdalsrsinfo', '-o', 'wkt', 'EPSG:4979']
    assert expected_arguments == subprocess_run.mock_values["gdalsrsinfo"]["arguments"]
    assert "the WKT" == subprocess_run.mock_values["gdalsrsinfo"]["stdout"]
    # check the output grid
    base_file = os.path.join(test_files_path, "transform_ugrid_points_tool", "ugrid_base.xmc")
    out_file = os.path.join(test_files_path, "transform_ugrid_points_tool", "grids", "ugrid_out.xmc")
    assert filecmp.cmp(base_file, out_file, shallow=False)


@mock.patch('xms.tool_runner.tools.transform_ugrid_points_tool.subprocess.run')
def test_transform_error(mock_subprocess_run, tool, test_files_path):
    """Test when gdaltransform fails."""
    # mock subprocess.run for gdaltransform and gdalsrsinfo
    subprocess_run = SubprocessRun()
    subprocess_run.mock_values["gdaltransform"]["failure"] = "gdaltransform failed!"
    mock_subprocess_run.side_effect = subprocess_run

    # set up the tool arguments
    arguments = tool.initial_arguments()
    arguments[tool.ARG_INPUT_GRID].value = "ugrid_in"
    arguments[tool.ARG_GDAL_TOOLS_PATH].value = "C:/Program Files/GDAL"
    arguments[tool.ARG_EPSG_CODE_FROM].value = 2956
    arguments[tool.ARG_EPSG_CODE_TO].value = 4329
    arguments[tool.ARG_OUTPUT_GRID].value = "ugrid_out"

    with pytest.raises(ToolError) as exception_info:
        tool.run_tool(arguments)
    assert "Unable to run gdaltransform" in str(exception_info.value)


@mock.patch('xms.tool_runner.tools.transform_ugrid_points_tool.subprocess.run')
def test_wkt_error(mock_subprocess_run, tool, test_files_path):
    """Test when gdaltransform fails."""
    # mock subprocess.run for gdaltransform and gdalsrsinfo
    subprocess_run = SubprocessRun()
    subprocess_run.mock_values["gdalsrsinfo"]["failure"] = "gdalsrsinfo failed!"
    mock_subprocess_run.side_effect = subprocess_run

    # set up the tool arguments
    arguments = tool.initial_arguments()
    arguments[tool.ARG_INPUT_GRID].value = "ugrid_in"
    arguments[tool.ARG_GDAL_TOOLS_PATH].value = "C:/Program Files/GDAL"
    arguments[tool.ARG_EPSG_CODE_FROM].value = 2956
    arguments[tool.ARG_EPSG_CODE_TO].value = 4329
    arguments[tool.ARG_OUTPUT_GRID].value = "ugrid_out"

    with pytest.raises(ToolError) as exception_info:
        tool.run_tool(arguments)
    assert "Unable to retrieve WKT for EPSG code" in str(exception_info.value)
