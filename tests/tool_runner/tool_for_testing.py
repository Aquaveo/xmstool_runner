"""Tool used for testing."""

__copyright__ = "(C) Copyright Aquaveo 2020"
__license__ = "All rights reserved"

# 1. Standard python modules

# 2. Third party modules
import pandas as pd

# 3. Aquaveo modules
from xms.tool_core import IoDirection, Tool
from xms.tool_core.table_definition import FloatColumnType, TableDefinition

# 4. Local modules


def _test_df() -> pd.DataFrame:
    """Returns a dataframe for testing."""
    df = pd.DataFrame({'column1': [0.0, 1.0], 'column2': [0.1, 1.1]})
    df.index += 1
    return df


def _test_table_def() -> TableDefinition:
    """Returns a TableDefinition for testing."""
    return TableDefinition(column_types=[FloatColumnType(header='column1', tool_tip='column1'),
                                         FloatColumnType(header='column2', tool_tip='column2')])


class DummyResultsDialog:
    """Do nothing results dialog for testing."""

    def __init__(self, parent):
        """Constructor.

        Args:
            parent (QObject): The dialog's Qt parent, unused
        """
        pass

    def exec(self):
        """Do nothing override for exec method."""
        pass


class ToolForTesting(Tool):
    """Tool used for tests."""

    ARG_ONE = 0
    ARG_TWO = 1
    ARG_OPERATION = 2
    ARG_STRING_IN = 3
    ARG_STRING_OUT = 4
    ARG_GRID_IN = 5
    ARG_GRID_OUT = 6
    ARG_DATASET_IN = 7
    ARG_DATASET_OUT = 8
    ARG_FILE_IN = 9
    ARG_FILE_OUT = 10
    ARG_BOOL_IN = 11
    ARG_BOOL_OUT = 12
    ARG_TABLE_IN = 13

    def __init__(self, for_building_history=False, require_dataset=False):
        """Initializes the class."""
        super().__init__('Simple Addition')
        self._for_building_history = for_building_history
        self._require_dataset = require_dataset
        self.results_dialog_module = 'tests.tool_runner.tool_for_testing'
        self.results_dialog_class = 'DummyResultsDialog'

    def enable_arguments(self, arguments):
        """Called to show/hide arguments, change argument values and add new arguments.

        Args:
            arguments(list): The tool arguments.
        """
        if arguments[0].text_value == "5" or arguments[0].text_value == "5.0":
            arguments[1].value = "6"
            arguments[2].hide = True

    def initial_arguments(self):
        """Setup the initial arguments.

        Returns:
            (list): The initial arguments.
        """
        arguments = [
            self.integer_argument(name='one', description='Argument 1', value=1, min_value=-100, max_value=100),
            self.float_argument(name='two', description='Argument 2', io_direction=IoDirection.INPUT, value=2.0,
                                min_value=-100.0, max_value=100.0),
            self.string_argument(name='operation', description='Operation', value='Add', choices=['Add', 'Subtract']),
            self.string_argument(name='string_in', description='Message', io_direction=IoDirection.INPUT, value=''),
            self.string_argument(name='string_out', description='Output', io_direction=IoDirection.OUTPUT, value=''),
            self.grid_argument(name='grid_in', description='An input UGrid', optional=True),
            self.grid_argument(name='grid_out', description='An output UGrid', io_direction=IoDirection.OUTPUT,
                               optional=True, value=''),
            self.dataset_argument(name='dataset_in', description='An input dataset',
                                  optional=not self._require_dataset),
            self.dataset_argument(name='dataset_out', description='An output dataset', io_direction=IoDirection.OUTPUT,
                                  optional=True, value=''),
            self.file_argument(name='file_in', description='An input file',
                               optional=True),
            self.file_argument(name='file_out', description='An output file', io_direction=IoDirection.OUTPUT,
                               optional=True),
            self.bool_argument(name='bool_in', description='Boolean in', value=True),
            self.bool_argument(name='bool_out', description='Boolean out', io_direction=IoDirection.OUTPUT),
            self.table_argument(name='table_in', description='Table in', io_direction=IoDirection.INPUT,
                                value=_test_df(), table_definition=_test_table_def())
        ]
        if self._for_building_history:
            """
                ARG_ONE = 0
                ARG_TWO = 1
                ARG_OPERATION = 2
                ARG_STRING_IN = 3
                ARG_STRING_OUT = 4
                ARG_GRID_IN = 5
                ARG_GRID_OUT = 6
                ARG_DATASET_IN = 7
                ARG_DATASET_OUT = 8
                ARG_FILE_IN = 9
                ARG_FILE_OUT = 10
                ARG_BOOL_IN = 11
                ARG_BOOL_OUT = 12
                ARG_TABLE_IN = 13
            """
            arguments[self.ARG_ONE].value = 1
            arguments[self.ARG_TWO].value = 0.5
            arguments[self.ARG_OPERATION].value = 'Subtract'
            arguments[self.ARG_STRING_IN].value = 'String In'
            arguments[self.ARG_STRING_OUT].value = None
            arguments[self.ARG_GRID_IN].value = 'UGrid 1'
            arguments[self.ARG_GRID_OUT].value = 'Output Grid'
            arguments[self.ARG_DATASET_IN].value = 'UGrid 1/Dset 1'
            arguments[self.ARG_DATASET_OUT].value = 'Output Dataset'
            arguments[self.ARG_FILE_IN].value = 'Input File'
            arguments[self.ARG_FILE_OUT].value = 'Output File'
            arguments[self.ARG_BOOL_IN].value = False
            arguments[self.ARG_BOOL_OUT].value = True
            arguments[self.ARG_TABLE_IN].value = _test_df()
        return arguments

    def validate_arguments(self, arguments):
        """Validate the tool arguments.

        Args:
            arguments (list): The tool arguments.

        Returns:
            (dict): Dictionary of errors with argument name as key.
        """
        errors = {}
        if arguments[0].value == 50:
            errors[arguments[0].name] = 'Can not equal 50.'
        return errors

    def run(self, arguments):
        """Run the tool.

        Args:
            arguments: The tool arguments.
        """
        if arguments[self.ARG_OPERATION].value != 'Add':
            arguments[self.ARG_STRING_IN].value = str(arguments[self.ARG_ONE].value - arguments[self.ARG_TWO].value)
            output = f'Difference of {arguments[self.ARG_ONE].value} and '
            output += f'{arguments[self.ARG_TWO].value} is {arguments[3].value}'
            self.logger.info(output)

        self.logger.info(f'Message is: {arguments[self.ARG_STRING_OUT].value}')
        self.logger.info(f'Grid is: {arguments[self.ARG_GRID_IN].value}')


class IntegerDivisionTool(Tool):
    """Tool to test integer arguments."""
    ARG_ONE = 0
    ARG_TWO = 1
    ARG_OUT = 2

    def __init__(self):
        """Initializes the class."""
        super().__init__('Integer Division')

    def initial_arguments(self):
        """Setup the initial arguments.

        Returns:
            (list): The initial arguments.
        """
        arguments = []

        argument1 = self.integer_argument(name='one', description='Argument 1')
        argument1.value = 1
        arguments.append(argument1)

        argument2 = self.integer_argument(name='two', description='Argument 2')
        argument2.value = 0
        arguments.append(argument2)

        argument3 = self.integer_argument(name='out', description='Output', io_direction=IoDirection.OUTPUT)
        arguments.append(argument3)

        return arguments

    def run(self, arguments):
        """Run the tool.

        Args:
            arguments: The tool arguments.
        """
        self.logger.info('Dividing two integers...')
        arguments[self.ARG_OUT].value = arguments[self.ARG_ONE].value / arguments[self.ARG_TWO].value
        self.logger.info(f'Result is {arguments[self.ARG_OUT].value}')
