"""Tests for Tool class."""

# 1. Standard python modules
import os

# 2. Third party modules

# 3. Aquaveo modules

# 4. Local modules
from xms.tool_runner.toolbox_history import ToolboxHistory

__copyright__ = "(C) Copyright Aquaveo 2020"
__license__ = "All rights reserved"


def test_read_history_file(test_files_path):
    """Test reading the history file."""
    project_folder = os.path.join(test_files_path, 'gila_tool_data')
    history = ToolboxHistory()
    history.read_history_file(project_folder)
    assert len(history.history) == 6
