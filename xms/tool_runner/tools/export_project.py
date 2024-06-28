"""Export a project into a folder for use with tools."""
# 1. Standard python modules
import logging
from pathlib import Path
import shlex

# 2. Third party modules
import h5py

# 3. Aquaveo modules
from xms.core.filesystem import filesystem as xfs

# 4. Local modules

__copyright__ = "(C) Copyright Aquaveo 2022"
__license__ = "All rights reserved"


def export_project(project_file: str, output_folder: str, logger: logging.Logger) -> None:
    """Export a project into a folder for use with tools.

    Args:
        project_file: The path to the project file to export.
        output_folder: The path to the new folder to contain the project files.
        logger: The logger.
    """
    logger.info('Getting a list of project files...')
    cards = _get_sms_project_cards(project_file)
    project_parent = Path(project_file).parent
    grids = _get_grids(cards, project_parent)
    _add_datasets(cards, project_parent, grids)
    logger.info('Copying project files...')
    _copy_files(grids, logger, output_folder)


def _get_sms_project_cards(project_file: str) -> list[list[str]]:
    """Get the cards in an SMS H5 project file.

    Args:
        project_file: The path to the project file.

    Returns:
        The cards.
    """
    cards = []
    with h5py.File(project_file) as file:
        card_dataset = file['SmsProject/Cards'][:]
        values_dataset = file['SmsProject/Values'][:]
        for i in range(len(card_dataset)):
            cards.append([card_dataset[i].decode('UTF-8'), values_dataset[i].decode('UTF-8')])
    return cards


def _get_grids(cards: list[list[str]], project_parent: Path) -> dict:
    """Get SMS project file's grids.

    Args:
        cards: The project file cards.
        project_parent: The parent path for writing the grids and datasets.

    Returns:
        A dictionary of grids by UUID.
    """
    grids = {}
    for card in cards:
        if card[0] == 'FILE':
            grid_path = card[1]
            grid_path = grid_path.strip()
            grid_path = grid_path.strip('"')
            grid_path = grid_path.replace('\\', '/')
            grid_path = project_parent / grid_path
            grid_path.resolve()
            with h5py.File(grid_path) as file:
                for item_name in file.keys():
                    group_item = file[item_name]
                    if isinstance(group_item, h5py.Group):
                        grid_name = group_item.name[1:]
                        uuid = group_item['PROPERTIES/GUID'][0].decode('UTF-8')
                        grids[uuid] = {'name': grid_name, 'file': grid_path.with_suffix('.xmc')}
    return grids


def _add_datasets(cards: list[list[str]], project_parent: Path, grids: dict):
    """Add datasets to dictionary of grids.

    Args:
        cards: The SMS project file cards.
        project_parent: The parent path for writing the grids and datasets.
        grids: A dictionary of grids by UUID.
    """
    for i in range(len(cards)):
        if cards[i][0] == 'GUID' and cards[i][1] in grids:
            uuid = cards[i][1]
            dset_idx = i + 1
            datasets = []
            while dset_idx < len(cards) and cards[dset_idx][0] == 'DS_XMDF':
                dataset_line = cards[dset_idx][1]
                dataset_line = dataset_line.replace('\\', '/')
                items = shlex.split(dataset_line)
                name = items[0]
                dataset_path = project_parent / items[1]
                dataset_path.resolve()
                datasets.append({'name': name, 'file': dataset_path})
                dset_idx += 1
            grids[uuid]['datasets'] = datasets


def _copy_files(grids: dict, logger: logging.Logger, output_folder: str):
    """Copy project files into a folder.

    Args:
        grids: A dictionary of grids by UUID.
        logger: The logger.
        output_folder: The folder to create and copy to.
    """
    grid_folder = Path(output_folder) / 'grids'
    grid_folder.mkdir(parents=True)
    for grid in grids.values():
        grid_name = grid['name']
        logger.info(f'Copying grid {grid_name}...')
        copy_to = grid_folder / grid_name
        copy_to = copy_to.with_suffix('.xmc')
        xfs.copyfile(str(grid['file']), str(copy_to))
        grid_datasets = grid['datasets']
        if len(grid_datasets) > 0:
            dataset_folder = grid_folder / grid_name
            dataset_folder.mkdir()
            for dataset in grid['datasets']:
                dataset_name = dataset['name']
                logger.info(f'Copying dataset {dataset_name}...')
                copy_to = dataset_folder / dataset_name
                copy_to = copy_to.with_suffix('.h5')
                parent_path = copy_to.parent
                parent_path.mkdir(parents=True, exist_ok=True)
                xfs.copyfile(str(dataset['file']), str(copy_to))
