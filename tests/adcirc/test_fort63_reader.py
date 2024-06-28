"""Tests fort13 io."""
# 1. Standard python modules
import logging
import os

# 2. Third party modules
import pytest

# 3. Aquaveo modules

# 4. Local modules
from tests.compare_datasets import assert_dataset_files_equal
from xms.adcirc.fort63_reader import Fort63Reader

__copyright__ = "(C) Copyright Aquaveo 2024"
__license__ = "All rights reserved"


@pytest.fixture
def files_dir() -> str:
    """
    Fixture method that returns the path to the directory containing the test files for the ADCIRC fort.63 reader.

    Returns:
        A string representing the file path to the directory.
    """
    directory = os.path.normpath(
        os.path.join(os.path.dirname(__file__), os.pardir, 'files', 'adcirc', 'test_fort_63_reader')
    )
    yield directory


def create_fort63_reader(files_dir: str, case_folder: str, in_file_name: str, geom_uuid: str, geom_num_nodes: int,
                         logger: logging.Logger = None):
    """
    Creates a Fort63Reader object for reading "fort.63.nc" files.

    Args:
        files_dir: Test files directory.
        case_folder: Test case folder.
        in_file_name: The name of the fort.63 file.
        geom_uuid: The UUID of the geometry object associated with the fort.63 file.
        geom_num_nodes: The number of nodes in the geometry object.
        logger: The logger.

    Returns:
        A Fort63Reader object for reading the fort.63 file.
    """
    case_path = os.path.join(files_dir, case_folder)
    input_path = os.path.join(case_path, 'input')
    input_file = os.path.join(input_path, in_file_name)
    fort63_reader = Fort63Reader(input_file, 'Water Surface (eta)', geom_uuid, geom_num_nodes, logger)
    return fort63_reader


def test_read(files_dir: str):
    """Tests importing a fort.63 with blank lines in between the attribute value blocks."""
    fort63_reader = create_fort63_reader(files_dir,
                                         'test_read',
                                         'fort.63.nc',
                                         '00000000-0000-0000-0000-000000000000',
                                         1586)
    fort63_reader.dset_uuid = '4fd375ef-4f34-44da-85fc-94a818388587'
    fort63_reader.read()
    dataset_out = fort63_reader.dataset_writer.h5_filename
    dataset_base = os.path.join(files_dir, 'test_read', 'base', 'Water Surface (eta).h5')
    assert_dataset_files_equal(dataset_base, dataset_out)


def test_logger(files_dir, caplog):
    """Test passing logger."""
    logger = logging.getLogger(__name__)
    fort63_reader = create_fort63_reader(files_dir,
                                         'test_read',
                                         'fort.63.nc',
                                         '00000000-0000-0000-0000-000000000000',
                                         1586,
                                         logger)
    with caplog.at_level(logging.INFO):
        fort63_reader.read()
    assert 'Reading "Water Surface (eta)" values from fort.63.nc.' in caplog.text
    assert 'Writing the "Water Surface (eta)" dataset values.' in caplog.text


def test_input_file_not_found(files_dir):
    """Test error when input file does not exist."""
    fort63_reader = create_fort63_reader(files_dir,
                                         'missing_case_folder',
                                         'missing.fort.63.nc',
                                         '00000000-0000-0000-0000-000000000000',
                                         10)
    with pytest.raises(FileNotFoundError) as file_error:
        fort63_reader.read()
    assert 'No such file or directory' in str(file_error.value)


def test_incorrect_number_of_values(files_dir):
    """Test error when fort.63.nc file has incorrect number of values."""
    fort63_reader = create_fort63_reader(files_dir,
                                         'test_read',
                                         'fort.63.nc',
                                         '00000000-0000-0000-0000-000000000000',
                                         9)
    with pytest.raises(ValueError) as value_error:
        fort63_reader.read()
    assert 'Incorrect number of values' in str(value_error.value)
