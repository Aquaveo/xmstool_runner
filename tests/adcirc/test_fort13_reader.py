"""Tests fort13 io."""
# 1. Standard python modules
import logging
import os

# 2. Third party modules
import pytest

# 3. Aquaveo modules

# 4. Local modules
from xms.adcirc.fort13_reader import Fort13Reader

__copyright__ = "(C) Copyright Aquaveo 2024"
__license__ = "All rights reserved"


@pytest.fixture
def files_dir() -> str:
    """
    Fixture method that returns the path to the directory containing the test files for the ADCIRC fort.13 reader.

    Returns:
        A string representing the file path to the directory.
    """
    directory = os.path.normpath(
        os.path.join(os.path.dirname(__file__), os.pardir, 'files', 'adcirc', 'test_fort_13_reader')
    )
    yield directory


def create_fort13_reader(files_dir: str, case_folder: str, in_file_name: str, geom_uuid: str, geom_num_nodes: int,
                         logger: logging.Logger = None):
    """
    Creates a Fort13Reader object for reading Fort.13 files.

    Args:
        files_dir: Test files directory.
        case_folder: Test case folder.
        in_file_name: The name of the fort.13 file.
        geom_uuid: The UUID of the geometry object associated with the fort.13 file.
        geom_num_nodes: The number of nodes in the geometry object.
        logger: The logger.

    Returns:
        A Fort13Reader object for reading the fort.13 file.
    """
    case_path = os.path.join(files_dir, case_folder)
    input_path = os.path.join(case_path, 'input')
    input_file = os.path.join(input_path, in_file_name)
    fort13_reader = Fort13Reader(input_file, geom_uuid, geom_num_nodes, logger)
    return fort13_reader


def test_with_blank_lines(files_dir: str):
    """Tests importing a fort.13 with blank lines in between the attribute value blocks."""
    fort13_reader = create_fort13_reader(files_dir,
                                         'test_with_blank_lines',
                                         'fort.13',
                                         '00000000-0000-0000-0000-000000000000',
                                         1586)
    fort13_reader.read()
    assert len(fort13_reader._att_dsets) == 2
    assert fort13_reader._num_atts == 3
    assert list(fort13_reader.datasets.keys()) == ['Z0b_var', 'BK', 'BAlpha', 'BDelX', 'POAN']


def test_unknown_attribute(files_dir: str):
    """Tests importing a fort.13 with an unknown attribute name."""
    fort13_reader = create_fort13_reader(files_dir,
                                         'test_unknown_attribute',
                                         'fort.13',
                                         '00000000-0000-0000-0000-000000000000',
                                         1586)
    fort13_reader.read()
    assert len(fort13_reader._att_dsets) == 2
    assert fort13_reader._num_atts == 3
    assert list(fort13_reader.datasets.keys()) == ['unknown_attribute_name', 'BK', 'BAlpha', 'BDelX', 'POAN']


def test_logger(files_dir, caplog):
    """Test passing logger."""
    logger = logging.getLogger(__name__)
    fort13_reader = create_fort13_reader(files_dir,
                                         'test_with_blank_lines',
                                         'fort.13',
                                         '00000000-0000-0000-0000-000000000000',
                                         1586,
                                         logger)
    with caplog.at_level(logging.INFO):
        fort13_reader.read()
    assert 'Reading nodal attribute properties...' in caplog.text
    assert 'Creating dataset ' in caplog.text
    assert 'Successfully read ADCIRC nodal attributes' in caplog.text
    assert list(fort13_reader.datasets.keys()) == ['Z0b_var', 'BK', 'BAlpha', 'BDelX', 'POAN']


def test_input_file_not_found(files_dir):
    """Test error when input file does not exist."""
    fort13_reader = create_fort13_reader(files_dir,
                                         'missing_case_folder',
                                         'missing.fort.13',
                                         '00000000-0000-0000-0000-000000000000',
                                         10)
    with pytest.raises(ValueError) as value_error:
        fort13_reader.read()
    assert 'File not found' in str(value_error.value)


def test_zero_nodes(files_dir):
    """Test error when fort.13 file has zero nodes."""
    fort13_reader = create_fort13_reader(files_dir,
                                         'test_with_zero_nodes',
                                         'fort.13',
                                         '00000000-0000-0000-0000-000000000000',
                                         0)
    with pytest.raises(ValueError) as value_error:
        fort13_reader.read()
    assert 'Invalid fort.13 file.' in str(value_error.value)


def test_node_number_mismatch(files_dir):
    """Test error when fort.13 file has zero nodes."""
    fort13_reader = create_fort13_reader(files_dir,
                                         'test_node_number_mismatch',
                                         'fort.13',
                                         '00000000-0000-0000-0000-000000000000',
                                         9)
    with pytest.raises(ValueError) as value_error:
        fort13_reader.read()
    assert 'Invalid number of nodes.' in str(value_error.value)


def test_no_nodal_attributes(files_dir):
    """Test error when no nodal attributes."""
    fort13_reader = create_fort13_reader(files_dir,
                                         'test_no_nodal_attributes',
                                         'fort.13',
                                         '00000000-0000-0000-0000-000000000000',
                                         10)
    with pytest.raises(ValueError) as value_error:
        fort13_reader.read()
    assert 'contains no nodal attributes' in str(value_error)
