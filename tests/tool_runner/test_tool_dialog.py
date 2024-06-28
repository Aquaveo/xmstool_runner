"""Tests for Tool class."""

# 1. Standard python modules
import filecmp
import json
import os
import unittest
from unittest.mock import MagicMock, Mock, patch

# 2. Third party modules
from PySide6.QtCore import QObject
from PySide6.QtWidgets import QDialog, QVBoxLayout
import pytest

# 3. Aquaveo modules
from xms.guipy.dialogs.xms_parent_dlg import ensure_qapplication_exists
from xms.guipy.testing.gui_test_helper import GuiTestHelper
from xms.tool_core import Argument, DataHandler, IoDirection
from xms.tool_gui.param_qt_helper import ParamQtHelper
from xms.tool_gui.tool_dialog import (clear_layout, get_test_files_path, run_tool_dialog, run_tool_with_feedback,
                                      ToolDialog)

# 4. Local modules
from tests.tool_runner.tool_for_testing import IntegerDivisionTool, ToolForTesting

__copyright__ = "(C) Copyright Aquaveo 2020"
__license__ = "All rights reserved"


class ToolTests(unittest.TestCase):
    """Tests for ToolRunner dialog."""

    @classmethod
    def setUpClass(cls) -> None:
        """Setup class for GUI tests."""
        ensure_qapplication_exists()
        os.environ['XMSTOOL_GUI_TESTING'] = 'YES'

    def _test_data_handler(self) -> DataHandler:
        """Get a DataHandler for testing.

        Returns:
            The data handler.
        """
        path = os.path.join(get_test_files_path(), 'Project')
        data_handler = DataHandler(path)
        return data_handler

    def _test_files_folder(self):
        """
        Get the test files folder.

        Returns:
            (str): The test files folder.
        """
        return get_test_files_path()

    def test_initial_default_arguments(self):
        """Test initial default arguments get loaded into the tool settings dialog."""
        win_cont = None
        tool = ToolForTesting()
        tool.echo_output = False
        tool.set_gui_data_folder(get_test_files_path())
        tool_arguments = [
            tool.integer_argument(name='one', description='Argument 1', value=1, min_value=-100, max_value=100),
            tool.float_argument(name='two', description='Argument 2', io_direction=IoDirection.INPUT, value=2.0,
                                min_value=-100.0, max_value=100.0),
            tool.string_argument(name='operation', description='Operation', value='Add',
                                 choices=['Add', 'Subtract']),
            tool.string_argument(name='string_in', description='Message', io_direction=IoDirection.INPUT,
                                 value=''),
            tool.string_argument(name='string_out', description='Output', io_direction=IoDirection.OUTPUT,
                                 value=''),
            tool.grid_argument(name='grid_in', description='An input UGrid', value='5 Cell Grid'),
            tool.grid_argument(name='grid_out', description='An output UGrid', io_direction=IoDirection.OUTPUT,
                               value=''),
            tool.dataset_argument(name='dataset_in', description='An input dataset', value='Z'),
            tool.dataset_argument(name='dataset_out', description='An output dataset',
                                  io_direction=IoDirection.OUTPUT),
        ]
        dialog = ToolDialog(win_cont, tool, tool_arguments)
        assert dialog is not None

        widget_names = dialog.get_param_widget_names()
        expected_widget_names = [
            'one',
            'two',
            'operation',
            'string_in',
            'grid_in',
            'grid_out',
            'dataset_in',
            'dataset_out'
        ]
        assert expected_widget_names == widget_names

        # test initial values
        assert '1' == dialog.get_param_widget('one').text()
        assert '2.0' == dialog.get_param_widget('two').text()
        assert 'Add' == dialog.get_param_widget('operation').currentText()
        assert '' == dialog.get_param_widget('string_in').text()
        assert '5 Cell Grid' == dialog.get_param_widget('grid_in').currentText()
        assert '' == dialog.get_param_widget('grid_out').text()
        assert 'Z' == dialog.get_param_widget('dataset_in').currentText()
        assert '' == dialog.get_param_widget('dataset_out').text()

    def test_initial_rerun_arguments(self):
        """Test initial arguments from rerun JSON get loaded into the tool settings dialog."""
        data_handler = self._test_data_handler()

        tool = ToolForTesting()
        tool.set_data_handler(data_handler)
        tool.echo_output = False

        input_file = os.path.join(get_test_files_path(), 'tool_results.json')
        with open(input_file) as json_file:
            json_object = json.load(json_file)
        if 'arguments' in json_object:
            tool_arguments = tool.get_arguments_from_results(json_object)

        win_cont = None
        dialog = ToolDialog(win_cont, tool, tool_arguments, title='Tool Settings')
        assert dialog is not None

        widget_names = dialog.get_param_widget_names()
        expected_widget_names = [
            'one',
            'two',
            'operation',
            'string_in',
            'grid_in',
            'grid_out',
            'dataset_in',
            'dataset_out'
        ]
        assert expected_widget_names == widget_names
        assert dialog.get_param_widget('bogus') is None

        # test initial values
        assert '2' == dialog.get_param_widget('one').text()
        assert '3.0' == dialog.get_param_widget('two').text()
        assert 'Subtract' == dialog.get_param_widget('operation').currentText()
        assert 'Hello World!' == dialog.get_param_widget('string_in').text()
        assert 'UGrid 2' == dialog.get_param_widget('grid_in').currentText()
        assert 'UGrid 3' == dialog.get_param_widget('grid_out').text()
        assert 'UGrid 2/Dset 3' == dialog.get_param_widget('dataset_in').currentText()
        assert 'UGrid 3/Dset 4' == dialog.get_param_widget('dataset_out').text()

        dialog.accept()
        dialog.close()
        tool.run_tool(tool_arguments)
        output = tool.get_testing_output()
        expected_output = (
            'Running tool "Simple Addition"...\n'
            "Input parameters: {'one': 2, 'two': 3.0, 'operation': Subtract, 'string_in': Hello World!, "
            "'string_out': , 'grid_in': UGrid 2, 'grid_out': UGrid 3, 'dataset_in': UGrid 2/Dset 3, "
            "'dataset_out': UGrid 3/Dset 4}\n"
            'Difference of 2 and 3.0 is -1.0\n'
            'Message is: None\n'
            'Grid is: UGrid 2\n'
            'Completed tool "Simple Addition"\n')
        assert expected_output == output

    def test_correct_arguments_from_dialog(self):
        """Test changing arguments in the tool settings dialog."""
        data_handler = self._test_data_handler()

        tool = ToolForTesting()
        tool.set_data_handler(data_handler)
        tool.echo_output = False
        tool_arguments = tool.initial_arguments()

        win_cont = None
        dialog = ToolDialog(win_cont, tool, tool_arguments)
        assert dialog is not None

        widget_names = dialog.get_param_widget_names()
        expected_widget_names = [
            'one',
            'two',
            'operation',
            'string_in',
            'grid_in',
            'grid_out',
            'dataset_in',
            'dataset_out',
            'file_in',
            'file_out',
            'bool_in',
            'table_in'
        ]
        assert expected_widget_names == widget_names

        # argument 0
        dialog.get_param_widget('one').setText('2')
        dialog.get_param_widget('one').editingFinished.emit()

        # argument 1
        dialog.get_param_widget('two').setText('3.0')
        dialog.get_param_widget('two').editingFinished.emit()

        # argument 2
        dialog.get_param_widget('operation').setCurrentText('Subtract')
        dialog.get_param_widget('operation').currentTextChanged.emit('Subtract')

        dialog.get_param_widget('string_in').setText('Hello World!')
        dialog.get_param_widget('string_in').editingFinished.emit()

        dialog.get_param_widget('grid_in').setCurrentText('UGrid 2')
        dialog.get_param_widget('grid_in').currentTextChanged.emit('UGrid 2')

        dialog.get_param_widget('grid_out').setText('UGrid 3')
        dialog.get_param_widget('grid_out').editingFinished.emit()

        dialog.get_param_widget('dataset_in').setCurrentText('UGrid 2/Dset 3')
        dialog.get_param_widget('dataset_in').currentTextChanged.emit('UGrid 2/Dset 3')
        dialog.get_param_widget('dataset_out').setText('UGrid 3/Dset 4')
        dialog.get_param_widget('dataset_out').editingFinished.emit()
        GuiTestHelper.process_events()

        # test initial values
        assert '2' == dialog.get_param_widget('one').text()
        assert '3.0' == dialog.get_param_widget('two').text()
        assert 'Subtract' == dialog.get_param_widget('operation').currentText()
        assert 'Hello World!' == dialog.get_param_widget('string_in').text()
        assert 'UGrid 2' == dialog.get_param_widget('grid_in').currentText()
        assert 'UGrid 3' == dialog.get_param_widget('grid_out').text()
        assert 'UGrid 2/Dset 3' == dialog.get_param_widget('dataset_in').currentText()
        assert 'UGrid 3/Dset 4' == dialog.get_param_widget('dataset_out').text()

        # lets you enter out of range value and later pops up an alert
        dialog.get_param_widget('one').setText('101')
        dialog.get_param_widget('one').editingFinished.emit()
        dialog.get_param_widget('two').setText('-101.0')
        dialog.get_param_widget('two').editingFinished.emit()
        GuiTestHelper.process_events()
        assert '101' == dialog.get_param_widget('one').text()
        assert '-101.0' == dialog.get_param_widget('two').text()
        dialog.close()

    @patch('xms.tool_gui.tool_dialog.message_with_ok')
    def test_report_bad_arguments(self, mock_message_with_ok):
        """Test reporting bad arguments for the tool settings dialog."""
        data_handler = self._test_data_handler()

        tool = ToolForTesting()
        tool.set_data_handler(data_handler)
        tool.echo_output = False
        tool_arguments = tool.initial_arguments()

        win_cont = None
        dialog = ToolDialog(win_cont, tool, tool_arguments)
        assert dialog is not None
        dialog.show()

        widget_names = dialog.get_param_widget_names()
        expected_widget_names = [
            'one',
            'two',
            'operation',
            'string_in',
            'grid_in',
            'grid_out',
            'dataset_in',
            'dataset_out',
            'file_in',
            'file_out',
            'bool_in',
            'table_in'
        ]
        assert expected_widget_names == widget_names

        dialog.get_param_widget('one').setText('50')
        dialog.get_param_widget('one').editingFinished.emit()
        dialog.get_param_widget('two').setText('-101.0')
        dialog.get_param_widget('two').editingFinished.emit()

        dialog.accept()
        dialog.close()
        expected_message = ('Invalid arguments:\n'
                            'Argument 2: Value must be greater than -100.0.')
        assert (dialog, expected_message, 'Simple Addition') == mock_message_with_ok.call_args[0]

    def test_hide_argument(self):
        """Test changing and hiding arguments based on value of another argument."""
        data_handler = self._test_data_handler()

        tool = ToolForTesting()
        tool.set_data_handler(data_handler)
        tool.echo_output = False
        tool_arguments = tool.initial_arguments()

        win_cont = None
        dialog = ToolDialog(win_cont, tool, tool_arguments)
        assert dialog is not None
        assert '' == dialog.tool_url  # Should be no URL for this tool

        widget_names = dialog.get_param_widget_names()
        expected_widget_names = [
            'one',
            'two',
            'operation',
            'string_in',
            'grid_in',
            'grid_out',
            'dataset_in',
            'dataset_out',
            'file_in',
            'file_out',
            'bool_in',
            'table_in'
        ]
        assert expected_widget_names == widget_names

        assert '1' == dialog.get_param_widget('one').text()
        assert '2.0' == dialog.get_param_widget('two').text()
        assert 'Add' == dialog.get_param_widget('operation').currentText()
        assert '' == dialog.get_param_widget('string_in').text()
        assert Argument.NONE_SELECTED == dialog.get_param_widget('grid_in').currentText()
        assert '' == dialog.get_param_widget('grid_out').text()
        assert Argument.NONE_SELECTED == dialog.get_param_widget('dataset_in').currentText()
        assert '' == dialog.get_param_widget('dataset_out').text()

        dialog.get_param_widget('one').setText('5')
        dialog.get_param_widget('one').editingFinished.emit()
        GuiTestHelper.process_events()

        assert '5' == dialog.get_param_widget('one').text()
        assert '6.0' == dialog.get_param_widget('two').text()
        assert dialog.get_param_widget('operation') is None
        assert '' == dialog.get_param_widget('string_in').text()
        assert Argument.NONE_SELECTED == dialog.get_param_widget('grid_in').currentText()
        assert '' == dialog.get_param_widget('grid_out').text()
        assert Argument.NONE_SELECTED == dialog.get_param_widget('dataset_in').currentText()
        assert '' == dialog.get_param_widget('dataset_out').text()
        dialog.close()

    def test_run_tool(self):
        """Test running tool from the tool settings dialog."""
        data_handler = self._test_data_handler()

        tool = ToolForTesting()
        tool.set_data_handler(data_handler)
        tool.echo_output = False
        tool_arguments = tool.initial_arguments()
        tool_arguments[tool.ARG_DATASET_OUT].value = 'dataset_out'
        run_tool_with_feedback(None, tool, tool_arguments, modal=True)
        message = tool.get_testing_output()
        assert message.find('Completed tool') >= 0

    def test_run_tool_with_error(self):
        """Test running tool from the tool settings dialog."""
        data_handler = self._test_data_handler()

        tool = ToolForTesting(require_dataset=True)
        tool.set_data_handler(data_handler)
        tool.echo_output = False
        tool.run_tool = Mock(side_effect=RuntimeError('Test error'))
        tool_arguments = tool.initial_arguments()
        run_tool_with_feedback(None, tool, tool_arguments)
        message = tool.get_testing_output()
        assert message == ''

    def test_run_tool_with_exception(self):
        """Test running tool that throws an exception."""
        tool = IntegerDivisionTool()
        tool.echo_output = False
        tool_arguments = tool.initial_arguments()
        run_tool_with_feedback(None, tool, tool_arguments)
        expected_output = (
            'Running tool "Integer Division"...\n'
            "Input parameters: {'one': 1, 'two': 0, 'out': }\n"
            'Dividing two integers...\n'
            'Problem running tool "Integer Division".  More information:\n'
            'division by zero\n'
        )
        output = tool.get_testing_output()
        assert output == expected_output
        output = tool.results['output']
        assert 'Traceback' in output
        assert 'ZeroDivisionError: division by zero' in output
        assert tool_arguments[tool.ARG_OUT].value is None
        assert tool.results['status'] == 'failure'

    @patch('webbrowser.open')
    def test_help_button(self, mock_open_web_page: MagicMock):
        """Test opening help web page."""
        data_handler = self._test_data_handler()

        tool = ToolForTesting(for_building_history=True)
        tool.set_data_handler(data_handler)
        tool.echo_output = False
        tool_arguments = tool.initial_arguments()
        dialog = ToolDialog(None, tool, tool_arguments)
        # with tool_url set
        dialog.tool_url = 'https://www.aquaveo.com/'
        assert dialog is not None
        dialog.help_requested()
        mock_open_web_page.assert_called_with(dialog.tool_url)
        # without tool_url set
        dialog.tool_url = None
        dialog.help_requested()
        mock_open_web_page.assert_called_with('https://www.xmswiki.com')
        dialog.close()

    def test_find_wiki_url(self):
        """Test finding the url for a tool that has a wiki page.

        Notes:
            This isn't the greatest test because it relies on setting the module of a tool to be a currently valid one
            in xmstool.
        """
        data_handler = self._test_data_handler()

        tool = ToolForTesting()
        tool.set_data_handler(data_handler)
        tool.echo_output = False
        tool_arguments = tool.initial_arguments()
        # Check URL for Compare Datasets Tool
        dialog = ToolDialog(None, tool, tool_arguments, tool_uuid='425a4115-d334-4d06-94d7-e3e140870299')
        assert dialog is not None
        dialog.update_tool_help_url()
        assert dialog.tool_url.find('xmswiki.com') > 0  # Should be a URL for this tool
        dialog.close()

    def test_load_tool_help(self):
        """Test loading tool help web page.
        """
        data_handler = self._test_data_handler()

        tool = ToolForTesting()
        tool.set_data_handler(data_handler)
        tool.echo_output = False
        tool_arguments = tool.initial_arguments()
        # I know this is hackish, but it is how the dialog determines if a tool has a linked wiki page.
        tool.__module__ = 'xms.tool.datasets.compare_datasets_tool'
        tool_file = os.path.join(get_test_files_path(), 'tool_help.html')
        tool_file = tool_file.replace('\\', '/')
        tool_url = 'file:///' + tool_file
        dialog = ToolDialog(None, tool, tool_arguments, tool_url=tool_url)
        assert dialog is not None
        while not dialog.web_page_loaded:
            GuiTestHelper.process_events()
        assert 'Test Tool Help' == dialog.web_page.title()
        dialog.close()

    def test_error_loading_tool_help(self):
        """Test error loading tool help web page.
        """
        data_handler = self._test_data_handler()

        tool = ToolForTesting()
        tool.set_data_handler(data_handler)
        tool.echo_output = False
        tool_arguments = tool.initial_arguments()
        tool_file = os.path.join(get_test_files_path(), 'bogus.html')
        tool_file = tool_file.replace('\\', '/')
        tool_url = 'file:///' + tool_file
        dialog = ToolDialog(None, tool, tool_arguments, tool_url=tool_url)
        assert dialog is not None
        while not dialog.web_page_loaded:
            GuiTestHelper.process_events()
        assert dialog.web_load_error
        dialog.close()

    @patch.object(ToolDialog, 'exec')
    def test_run_tool_dialog(self, tool_exec_mock):
        """Test running the tool dialog when called from main."""
        tool_exec_mock.return_value = QDialog.Accepted
        data_handler = self._test_data_handler()

        tool = ToolForTesting()
        tool.set_data_handler(data_handler)
        tool.echo_output = False
        input_data = {}
        output_file = os.path.join(get_test_files_path(), 'run_tool_out.json')
        output_json = run_tool_dialog(input_data, None, tool)
        with open(output_file, "w") as out_file:
            json.dump(output_json, out_file, indent=4)
        base_file = os.path.join(get_test_files_path(), 'run_tool_base.json')
        assert filecmp.cmp(output_file, base_file)

    @patch.object(ToolDialog, 'exec')
    def test_run_tool_dialog_from_history(self, tool_exec_mock):
        """Test running the tool dialog when called from main using saved history."""
        tool_exec_mock.return_value = QDialog.Accepted
        data_handler = self._test_data_handler()

        tool = ToolForTesting()
        tool.set_data_handler(data_handler)
        tool.echo_output = False
        input_file = os.path.join(get_test_files_path(), 'run_tool_from_history_in.json')
        with open(input_file, "r") as in_file:
            input_data = json.load(in_file)
        output_file = os.path.join(get_test_files_path(), 'run_tool_from_history_out.json')
        output = run_tool_dialog(input_data, None, tool)
        with open(output_file, "w") as out_file:
            json.dump(output, out_file, indent=4)
        base_file = os.path.join(get_test_files_path(), 'run_tool_from_history_base.json')
        assert filecmp.cmp(output_file, base_file)

    @patch.object(ToolDialog, 'exec')
    def test_run_tool_dialog_from_override(self, tool_exec_mock):
        """Test running the tool dialog when called from main using argument value override."""
        tool_exec_mock.return_value = QDialog.Accepted
        data_handler = self._test_data_handler()

        tool = ToolForTesting()
        tool.set_data_handler(data_handler)
        tool.echo_output = False
        # query = None
        input_file = os.path.join(get_test_files_path(), 'run_tool_from_override_in.json')
        with open(input_file, "r") as in_file:
            input_data = json.load(in_file)
        output_file = os.path.join(get_test_files_path(), 'run_tool_from_override_out.json')
        output = run_tool_dialog(input_data, None, tool)
        with open(output_file, "w") as out_file:
            json.dump(output, out_file, indent=4)
        base_file = os.path.join(get_test_files_path(), 'run_tool_from_override_base.json')
        assert filecmp.cmp(output_file, base_file)

    @patch.object(ToolDialog, 'exec')
    @patch('xms.tool_gui.tool_dialog.message_with_ok')
    def test_run_tool_from_history_invalid_args(self, message_with_ok_mock, tool_exec_mock):
        """Test running the tool dialog when called from main using invalid saved history."""
        tool_exec_mock.return_value = QDialog.Accepted
        os.environ['XMS_PYTHON_APP_NAME'] = 'GMS'
        data_handler = self._test_data_handler()

        tool = ToolForTesting()
        tool.set_data_handler(data_handler)
        tool.echo_output = False
        # query = None
        input_file = os.path.join(get_test_files_path(), 'run_tool_invalid_args.json')
        with open(input_file, "r") as in_file:
            input_data = json.load(in_file)
        output_file = os.path.join(get_test_files_path(), 'run_tool_invalid_history_out.json')
        output = run_tool_dialog(input_data, None, tool)
        with open(output_file, "w") as out_file:
            json.dump(output, out_file, indent=4)
        expected_args = (
            'The arguments in the history do not match the current tool arguments. The default tool '
            'arguments will be used.')
        assert expected_args == message_with_ok_mock.call_args[0][1]
        base_file = os.path.join(get_test_files_path(), 'run_tool_base.json')
        assert filecmp.cmp(output_file, base_file)

    def test_clear_layout(self):
        """Test clear_layout."""
        data_handler = self._test_data_handler()
        tool = ToolForTesting()
        tool.set_data_handler(data_handler)
        tool.echo_output = False
        dialog = ToolDialog(None, tool, tool.initial_arguments())
        top_layout = dialog.widgets['top_layout']
        self.assertTrue(len(top_layout.children()) >= 1)
        clear_layout(dialog.widgets['top_layout'])
        self.assertTrue(len(top_layout.children()) == 0)

    def test_unsupported_param(self):
        """Test attempting to add widgets to layout for unsupported Param type."""
        parent_dialog = QObject()
        layout = QVBoxLayout()
        param_obj = {'type': 'Unsupported Type', 'name': 'argument_1', 'description': 'Argument 1'}
        param_qt_helper = ParamQtHelper(parent_dialog)
        with pytest.raises(RuntimeError) as runtime_error:
            param_qt_helper.add_param(layout, param_obj)
        assert str(runtime_error.value).startswith('Unsupported "param" parameter type: ')

    def test_empty_file_argument(self):
        """Test empty file argument retrieves empty string."""
        data_handler = self._test_data_handler()

        tool = ToolForTesting()
        tool.set_data_handler(data_handler)
        tool.echo_output = False
        tool_arguments = tool.initial_arguments()

        win_cont = None
        dialog = ToolDialog(win_cont, tool, tool_arguments)

        tool_arguments[tool.ARG_FILE_IN].value = 'wrong value'
        param_helper = dialog.param_helper
        param_helper.do_param_widgets('file_in')
        param_helper.on_end_do_param_widgets()
        assert '' == tool_arguments[tool.ARG_FILE_IN].value

        dialog.close()


def test_correct_arguments_from_dialog():
    """Test changing arguments in the tool settings dialog."""
    ensure_qapplication_exists()
    os.environ['XMSTOOL_GUI_TESTING'] = 'YES'
    path = os.path.join(get_test_files_path(), 'Project')
    data_handler = DataHandler(path)

    tool = ToolForTesting()
    tool.set_data_handler(data_handler)
    tool.echo_output = False
    tool_arguments = tool.initial_arguments()

    win_cont = None
    dialog = ToolDialog(win_cont, tool, tool_arguments)
    assert dialog is not None

    widget_names = dialog.get_param_widget_names()
    expected_widget_names = [
        'one',
        'two',
        'operation',
        'string_in',
        'grid_in',
        'grid_out',
        'dataset_in',
        'dataset_out',
        'file_in',
        'file_out',
        'bool_in',
        'table_in'
    ]
    assert expected_widget_names == widget_names

    # argument 0
    dialog.get_param_widget('one').setText('2')
    dialog.get_param_widget('one').editingFinished.emit()
    GuiTestHelper.process_events()
    assert '2' == dialog.get_param_widget('one').text()

    # # argument 1
    # dialog.get_param_widget('two').setText('3.0')
    # dialog.get_param_widget('two').editingFinished.emit()
    #
    # # argument 2
    # dialog.get_param_widget('operation').setCurrentText('Subtract')
    # dialog.get_param_widget('operation').currentTextChanged.emit('Subtract')
    #
    # dialog.get_param_widget('string_in').setText('Hello World!')
    # dialog.get_param_widget('string_in').editingFinished.emit()
    #
    # dialog.get_param_widget('grid_in').setCurrentText('UGrid 2')
    # dialog.get_param_widget('grid_in').currentTextChanged.emit('UGrid 2')
    #
    # dialog.get_param_widget('grid_out').setText('UGrid 3')
    # dialog.get_param_widget('grid_out').editingFinished.emit()
    #
    # dialog.get_param_widget('dataset_in').setCurrentText('UGrid 2/Dset 3')
    # dialog.get_param_widget('dataset_in').currentTextChanged.emit('UGrid 2/Dset 3')
    # dialog.get_param_widget('dataset_out').setText('UGrid 3/Dset 4')
    # dialog.get_param_widget('dataset_out').editingFinished.emit()
    # GuiTestHelper.process_events()
    #
    # # test initial values
    # assert '2' == dialog.get_param_widget('one').text()
    # assert '3.0' == dialog.get_param_widget('two').text()
    # assert 'Subtract' == dialog.get_param_widget('operation').currentText()
    # assert 'Hello World!' == dialog.get_param_widget('string_in').text()
    # assert 'UGrid 2' == dialog.get_param_widget('grid_in').currentText()
    # assert 'UGrid 3' == dialog.get_param_widget('grid_out').text()
    # assert 'UGrid 2/Dset 3' == dialog.get_param_widget('dataset_in').currentText()
    # assert 'UGrid 3/Dset 4' == dialog.get_param_widget('dataset_out').text()
    #
    # # lets you enter out of range value and later pops up an alert
    # dialog.get_param_widget('one').setText('101')
    # dialog.get_param_widget('one').editingFinished.emit()
    # dialog.get_param_widget('two').setText('-101.0')
    # dialog.get_param_widget('two').editingFinished.emit()
    # GuiTestHelper.process_events()
    # assert '101' == dialog.get_param_widget('one').text()
    # assert '-101.0' == dialog.get_param_widget('two').text()
    dialog.close()
