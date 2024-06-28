"""Compare two datasets."""

# 1. Standard python modules
import json
import os
from typing import Optional, Union

# 2. Third party modules
import numpy

# 3. Aquaveo modules
from xms.datasets.dataset_reader import DatasetReader

# 4. Local modules


__copyright__ = "(C) Aquaveo 2024"
__license__ = "All rights reserved"


def assert_dataset_files_equal(base_file: str, out_file: str, allow_close=False,
                               dataset_name: Optional[str] = None, group_path: Optional[str] = None) -> None:
    """Assert two dataset files are equal for testing.

    Args:
        base_file: The path to the base dataset file.
        out_file: The path to the output dataset file.
        allow_close: Should dataset values be close or all equal?
        dataset_name: The name of the dataset.
        group_path: The group path to the dataset.
    """
    file_name = os.path.basename(out_file)
    if group_path is None and dataset_name is None:
        dataset_name, _ = os.path.splitext(file_name)
    base_reader = get_dataset_reader(base_file, dataset_name=dataset_name, group_path=group_path)
    out_reader = get_dataset_reader(out_file, dataset_name=dataset_name, group_path=group_path)
    # compare metadata
    base_metadata = build_dataset_meta_dict(base_reader, 'uuid')
    out_metadata = build_dataset_meta_dict(out_reader, 'uuid')
    same_metadata = base_metadata == out_metadata
    # compare dataset values
    base_json = build_dataset_value_dict(base_reader, 'uuid')
    out_json = build_dataset_value_dict(out_reader, 'uuid')
    same_values = dataset_values_equal(base_json, out_json, allow_close)

    base_json_file = os.path.splitext(base_file)[0] + '_out.json'
    out_json_file = os.path.splitext(out_file)[0] + '.json'
    if not (same_metadata and same_values):  # pragma no cover - only hit on failure
        dump_dataset_json(base_file, 'uuid', dataset_name, base_json_file)
        dump_dataset_json(out_file, 'uuid', dataset_name, out_json_file)
    assert same_metadata and same_values, f'\nfiles differ:\n  {base_json_file}\n  {out_json_file}'


def get_dataset_reader(file: str, dataset_name: Optional[str] = None,
                       group_path: Optional[str] = None) -> DatasetReader:
    """Get a dataset's reader.

    Args:
        file: The dataset file.
        dataset_name: The dataset name.
        group_path: The group path to the dataset.

    Returns:
        A dataset reader.
    """
    basename = os.path.basename(file)
    if group_path is None and dataset_name is None:
        dataset_name, _ = os.path.splitext(basename)
    reader = DatasetReader(file, dset_name=dataset_name, group_path=group_path)
    return reader


def build_dataset_meta_dict(reader: DatasetReader, ignored_keys: Union[str, list[str]]) -> dict[str, object]:
    """Convert a dataset to a dictionary with metadata.

    Args:
        reader: The dataset.
        ignored_keys: The dictionary keys to remove.

    Returns:
        (dict): JSON compatible dictionary with dataset metadata.
    """
    dset_data = {
        'uuid': reader.uuid,
        'geom_uuid': reader.geom_uuid,
        'ref_time': str(reader.ref_time),
        'null_value': reader.null_value,
        'time_units': reader.time_units,
        'num_activity_values': reader.num_activity_values,
        'num_components': reader.num_components,
        'num_values': reader.num_values,
    }
    if isinstance(ignored_keys, str):
        ignored_keys = [ignored_keys]
    for key in ignored_keys:
        dset_data.pop(key, None)
    return dset_data


def dump_dataset_json(dataset_file: str, ignored_keys: Union[str, list[str]], dataset_name: Optional[str] = None,
                      output_file: Optional[str] = None) -> None:
    """Export a dataset in an H5 file to JSON.

    Args:
        dataset_file: The path to the H5 dataset file.
        ignored_keys: The dictionary keys to remove from the JSON dictionary.
        dataset_name: Optional dataset name. If not specified uses the base name of the file.
        output_file: Optional path to the output file.
    """
    if output_file is None:
        base_path, _ = os.path.splitext(dataset_file)
        output_file = f'{base_path}.json'
    dataset_json = dataset_to_dict(dataset_file, ignored_keys, dataset_name=dataset_name)
    for key, value in dataset_json.items():
        if isinstance(value, numpy.ndarray):
            dataset_json[key] = value.tolist()
    with open(output_file, 'w') as dataset_file:
        s = json.dumps(dataset_json, indent=4, sort_keys=True)
        dataset_file.write(s)
        dataset_file.write('\n')


def build_dataset_value_dict(reader: DatasetReader, ignored_keys: Union[str, list[str]]):
    """Convert a dataset to a dictionary with value data.

    Args:
        reader: The dataset.
        ignored_keys: The dictionary keys to remove.

    Returns:
        (dict): JSON compatible dictionary with dataset value data.
    """
    active_dset = None
    try:
        active_dset = reader.activity[()]
    except TypeError:
        pass
    dset_data = {
        'values': reader.values[()],
        'times': reader.times[()],
        'mins': reader.mins[()],
        'maxs': reader.maxs[()],
        'active': active_dset
    }
    if isinstance(ignored_keys, str):
        ignored_keys = [ignored_keys]
    for key in ignored_keys:
        dset_data.pop(key, None)
    return dset_data


def dataset_values_equal(base_json: dict, out_json: dict, allow_close) -> bool:
    """Determine if dataset values in JSON are equal.

    Args:
        base_json: Dictionary of base values (containing 'values', 'times', 'mins', 'maxs', 'active' numpy arrays).
        out_json: Dictionary of out values.
        allow_close: Should dataset values be close or all equal?

    Returns:
        True if values are equal.
    """
    same_values = True
    for value_type in ['values', 'times', 'mins', 'maxs', 'active']:
        out = out_json[value_type]
        base = base_json[value_type]
        out_is_none = out is None
        base_is_none = base is None
        if out_is_none and base_is_none:
            # when values are both None they are equal
            continue
        if value_type == 'active' and (out_is_none or base_is_none):
            # when only one has activity they are not equal
            same_values = False
        # compare numpy array of values
        same_values = same_values and out.shape == base.shape
        if allow_close:
            same_values = same_values and numpy.allclose(out, base, equal_nan=True)
        else:
            same_values = same_values and numpy.array_equal(out, base, equal_nan=True)
        if not same_values:
            break
    return same_values


def dataset_to_dict(file: str, ignored_keys: Union[str, list[str]],
                    dataset_name: Optional[str] = None):
    """Convert a dataset file to a dictionary.

    Args:
        file: The file to convert. File basename must be the same as the dataset name.
        ignored_keys: The dictionary keys to remove.
        dataset_name: The dataset name.

    Returns:
        (dict): JSON compatible dictionary describing the dataset.
    """
    reader = get_dataset_reader(file, dataset_name)
    dset_data = build_dataset_value_dict(reader, ignored_keys)
    metadata = build_dataset_meta_dict(reader, ignored_keys)
    dset_data.update(metadata)
    return dset_data
