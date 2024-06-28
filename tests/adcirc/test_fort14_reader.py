"""Tests for fort14_reader.py."""

# 1. Standard python modules
import filecmp
import logging
import os

# 2. Third party modules
import pytest

# 3. Aquaveo modules
from xms.constraint import read_grid_from_file
from xms.core.filesystem import filesystem as io_util

# 4. Local modules
from xms.adcirc import Fort14Reader
from xms.adcirc.fort14_reader import GEOGRAPHIC_WKT, LOCAL_METERS_WKT


__copyright__ = "(C) Copyright Aquaveo 2024"
__license__ = "All rights reserved"


@pytest.fixture
def files_dir() -> str:
    """
    Fixture method that returns the path to the directory containing the test files for the ADCIRC fort.14 reader.

    Returns:
        A string representing the file path to the directory.
    """
    directory = os.path.normpath(
        os.path.join(os.path.dirname(__file__), os.pardir, 'files', 'adcirc', 'test_fort_14_reader')
    )
    yield directory


def test_import(files_dir):
    """Test import of a fort.14."""
    case_folder = os.path.join(files_dir, 'test_import')
    out_folder = os.path.join(case_folder, 'out')
    input_folder = os.path.join(case_folder, 'input')
    baselines_folder = os.path.join(case_folder, 'baselines')
    io_util.make_or_clear_dir(out_folder)

    input_file = os.path.join(input_folder, 'fort.14')
    reader = Fort14Reader(input_file)
    grid_file = os.path.join(out_folder, 'apiA580.tmp')
    out_grid_file = os.path.join(out_folder, 'apiA580.tmp')
    co_grid_out, wkt = reader.read()
    base_grid_file = os.path.join(baselines_folder, 'apiA580.tmp')
    co_grid_base = read_grid_from_file(base_grid_file)
    co_grid_out.uuid = co_grid_base.uuid
    co_grid_out.write_to_file(out_grid_file)
    assert filecmp.cmp(base_grid_file, grid_file)
    assert wkt == LOCAL_METERS_WKT


def test_import_missing_file(files_dir):
    """Test importing a missing fort.14."""
    case_folder = os.path.join(files_dir, 'test_missing_path')
    input_folder = os.path.join(case_folder, 'bogus_input')
    input_file = os.path.join(input_folder, 'fort.14')
    reader = Fort14Reader(input_file)
    with pytest.raises(ValueError) as value_error:
        reader.read()
    assert 'File not found' in str(value_error.value)


def test_with_numbering_gaps(files_dir):
    """Tests importing a fort.14 with gaps in the node numbering."""
    case_folder = os.path.join(files_dir, 'test_with_numbering_gaps')
    input_file = os.path.join(case_folder, 'V11_trim.grd')
    reader = Fort14Reader(input_file)
    co_grid, wkt = reader.read()

    out_grid_file = os.path.join(case_folder, 'output.xmc')
    io_util.removefile(out_grid_file)
    base_grid_file = os.path.join(case_folder, 'base.xmc')
    co_grid_base = read_grid_from_file(base_grid_file)
    co_grid.uuid = co_grid_base.uuid
    co_grid.write_to_file(out_grid_file)
    assert wkt == GEOGRAPHIC_WKT
    assert filecmp.cmp(base_grid_file, out_grid_file)


def test_logger(files_dir, caplog):
    """Test passing logger."""
    case_folder = os.path.join(files_dir, 'test_logger')
    input_file = os.path.join(case_folder, 'fort.14')
    logger = logging.getLogger(__name__)
    reader = Fort14Reader(input_file, logger=logger)
    with caplog.at_level(logging.INFO):
        reader.read()
    assert 'Loading fort.14 from ASCII file...' in caplog.text
    assert 'Parsing mesh node locations...' in caplog.text
    assert 'Parsing mesh element definitions...' in caplog.text
    assert 'Building the UGrid...' in caplog.text
