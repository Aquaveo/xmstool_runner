"""Configuration file for pytest."""

# 1. Standard python modules
import os

# 2. Third party modules
import pytest

# 3. Aquaveo modules

# 4. Local modules


__copyright__ = "(C) Copyright Aquaveo 2024"
__license__ = "All rights reserved"


@pytest.fixture(scope='session', autouse=True)
def setup_temp_folder(tmp_path_factory):
    """Setup temporary folder for tests.

    Args:
        tmp_path_factory: Factory for making a temporary path.
    """
    temp_files = tmp_path_factory.mktemp('temp_files')
    os.environ['XMS_PYTHON_APP_TEMP_DIRECTORY'] = str(temp_files)


@pytest.fixture
def test_files_path():
    """Get the absolute path to the 'tests/files' directory."""
    file_dir = os.path.dirname(os.path.realpath(__file__))
    files_path = os.path.join(file_dir, 'files')
    yield os.path.abspath(files_path)
