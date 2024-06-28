"""Dialogs for choosing open/save file dialogs."""
# 1. Standard python modules
import os

# 2. Third party modules
from PySide6.QtWidgets import QFileDialog

# 3. Aquaveo modules

# 4. Local modules
from xms.guipy import settings


def get_save_filename(parent, selected_filter, file_filters, caption='Save', start_dir=None):
    """Get the name of a file to save to.

    Args:
        parent (QWidget): Dialog parent for the file selector dialog
        selected_filter (str): The file filter that should be selected in the file browser dialog
        file_filters (str): The file filter list that should be in the file browser dialog. Filters separated
            by ';;'
        caption (str): The dialog caption
        start_dir (str): Directory the dialog should start in.
            If None, see settings.get_file_browser_directory() for the resolution rules.

    Returns:
        (str): The selected filename. Empty string if None
    """
    # Prompt the user for a save location
    if start_dir is None or (not os.path.exists(start_dir) and not os.path.exists(os.path.dirname(start_dir))):
        start_dir = settings.get_file_browser_directory()
    filename, _ = QFileDialog.getSaveFileName(
        parent, caption, dir=start_dir, filter=file_filters, selectedFilter=selected_filter
    )
    if filename:
        settings.save_file_browser_directory(os.path.dirname(filename))
    return filename


def get_open_filename(parent, caption, file_filter, start_dir=None):
    """Display a file selector dialog.

    Args:
        parent (QWidget): The parent dialog
        caption (str): The dialog caption
        file_filter (str): File extension filter
        start_dir (str): Directory the dialog should start in.
            If None, see settings.get_file_browser_directory() for the resolution rules.

    Returns:
        (str): The selected file. Empty string if user canceled
    """
    if start_dir is None or not os.path.exists(start_dir):
        start_dir = settings.get_file_browser_directory()
    filename, _ = QFileDialog.getOpenFileName(parent=parent, caption=caption, dir=start_dir, filter=file_filter)
    if filename and os.path.isfile(filename):
        settings.save_file_browser_directory(os.path.dirname(filename))
    return filename


def get_open_filenames(parent, caption, file_filter='', start_dir=None):
    """Display a file selector dialog with multi-file select enabled.

    Args:
        parent (QWidget): The parent dialog
        caption (str): The dialog caption
        file_filter (str): File extension filter
        start_dir (str): Directory the dialog should start in. If None,
            see settings.get_file_browser_directory() for the resolution rules.

    Returns:
        (list): The selected files.
    """
    if start_dir and os.path.isfile(start_dir):  # Make sure we don't specify a filename for the start directory
        start_dir = os.path.dirname(start_dir)
    if start_dir is None or not os.path.isdir(start_dir):
        start_dir = settings.get_file_browser_directory()
    filenames, _ = QFileDialog.getOpenFileNames(parent=parent, caption=caption, dir=start_dir, filter=file_filter)
    if filenames:
        settings.save_file_browser_directory(os.path.dirname(filenames[0]))
    return filenames


def get_open_foldername(parent, caption, start_dir=None):
    """Display a directory selector dialog.

    Args:
        parent (QWidget): The parent dialog
        caption (str): The dialog caption
        start_dir (str): Directory the dialog should start in.
            If None, see settings.get_file_browser_directory() for the resolution rules.

    Returns:
        (str): The selected files.
    """
    if start_dir and os.path.isfile(start_dir):  # Make sure we don't specify a filename for the start directory
        start_dir = os.path.dirname(start_dir)
    if start_dir is None or not os.path.isdir(start_dir):
        start_dir = settings.get_file_browser_directory()
    selected_folder = QFileDialog.getExistingDirectory(parent=parent, caption=caption, dir=start_dir)
    if selected_folder:
        settings.save_file_browser_directory(selected_folder)
    return selected_folder
