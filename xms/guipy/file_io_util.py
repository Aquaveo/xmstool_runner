"""Utilities for file I/O."""

__copyright__ = "(C) Copyright Aquaveo 2022"
__license__ = "All rights reserved"

# 1. Standard python modules
import json
from json import JSONDecodeError
from pathlib import Path

# 2. Third party modules

# 3. Aquaveo modules

# 4. Local modules


def read_json_file(filepath: str | Path):
    """Reads the json file and returns a dict.

    Args:
        filepath (str|Path):

    Returns:
        A dict created from the json file.
    """
    data = {}
    filepath = Path(filepath) if filepath else Path()
    if not filepath.is_file():
        return data
    try:
        with open(filepath, 'r') as file:
            data = json.load(file)
    except JSONDecodeError:
        pass
    return data


def write_json_file(data, filepath: Path | str, indent: int = 4) -> None:
    """Saves the data dict to a .json file that's nicely formatted.

    Args:
        data: Some dict that is serializable to json.
        filepath (str | Path): file that will be written to.
        indent (int): The indentation used in the file to make it nicely formatted.
    """
    filepath = Path(filepath)
    with filepath.open('w', encoding='utf-8') as file:
        json.dump(data, file, ensure_ascii=False, indent=indent)
