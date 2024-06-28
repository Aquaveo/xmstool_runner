"""Interface for reading and writing to the XMS registry."""
# 1. Standard python modules
import os
from pathlib import Path

# 2. Third party modules
from PySide6.QtCore import QDir, QSettings
try:
    import winreg
except ImportError:
    winreg = None

# 3. Aquaveo modules
from xms.api.dmi import XmsEnvironment as XmEnv
from xms.guipy import file_io_util

# 4. Local modules

__copyright__ = "(C) Copyright Aquaveo 2019"
__license__ = "All rights reserved"

# Constants used with get_file_browser_directory() and save_file_browser_directory()
FILE_BROWSER_DIRECTORY_FILE_NAME = 'file_browser_directory.json'
DIRECTORY = 'directory'


def get_file_browser_directory() -> str:
    """Get the last saved directory a file browser was open in.

    See Also:
         save_file_browser_directory()

    We look for and return the directory by searching in the following order:

    1) Check for last saved directory in temp directory. save_file_browser_directory() saves it here so that we
    remember it as long as we're still running the current instance of XMS.
    2) Use project path, if we have one
    3) Use 'Documents' folder

    Return:
        (str): The last saved file browser location. Root of the current drive if not set.
    """
    path = Path(XmEnv.xms_environ_temp_directory()) / FILE_BROWSER_DIRECTORY_FILE_NAME
    if path.is_file():
        data = file_io_util.read_json_file(path)
        directory = data.get(DIRECTORY)
        if directory:
            return directory

    project_path = XmEnv.xms_environ_project_path()
    if os.path.exists(project_path):
        return project_path

    return os.path.join(QDir.homePath(), 'Documents')


def save_file_browser_directory(folder_path: str | Path) -> None:
    """Set the last directory a file browser was open in.

    Call this after every time you open a file browser dialog.
    """
    path = Path(XmEnv.xms_environ_temp_directory()) / FILE_BROWSER_DIRECTORY_FILE_NAME
    file_io_util.write_json_file({DIRECTORY: str(folder_path)}, path)


class SettingsManager:
    """Interface for reading/writing package-level registry settings."""
    def __init__(self, python_path=True):
        """Initialize manager based on the XMS app that launched Python.

        Args:
            python_path (bool): If true, the base path in the registry will be to the Python folder
                below the app.
        """
        self._python_path = python_path
        # Environment variables will not exist if not running Python from XMS.
        self._app_name = os.environ.get('XMS_PYTHON_APP_NAME')
        self._app_version = os.environ.get('XMS_PYTHON_APP_VERSION')

    def _get_settings_path(self):
        """Get the path to the registry settings key for this instance of Python."""
        if not self._app_name:
            return None
        path = f"EMRL\\{self._app_name}\\{self._app_name} {self._app_version} (64-bit)"
        if self._python_path:
            path = f"{path}\\Python"
        return path

    def save_setting(self, package, key, value, reg_format=None):
        """Store a setting in the registry.

        Args:
            package (str): Name of the Python package the setting is for
            key (str): Key for the setting
            value (object): Value of the setting. str, int, float
            reg_format (winreg Value Types enum): If provided, should specify the specific registry type to write
                this value as. Useful when you need to write values that are compatible with old code.
        """
        reg_path = self._get_settings_path()
        if not reg_path:
            return
        if reg_format is not None:  # Use Windows calls to write specific data type
            reg_path = f'SOFTWARE\\{reg_path}\\{package}'
            if winreg is not None:
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, reg_path, 0, winreg.KEY_WRITE) as reg_key:
                    winreg.SetValueEx(reg_key, key, 0, reg_format, value)
        else:
            settings = QSettings(reg_path, package)
            settings.setValue(key, value)

    def get_setting(self, package, key, default=None):
        """Retrieve a setting from the registry.

        Args:
            package (str): Name of the Python package the setting is for
            key (str): Key for the setting
            default (object): Default object to return if setting is not found in the registry

        Returns:
            (object): The setting's value, or default if the setting was not found
        """
        reg_path = self._get_settings_path()
        if not reg_path:
            return default
        settings = QSettings(reg_path, package)
        value = settings.value(key)  # defaultValue kwarg doesn't seem to work here
        if value is None:
            return default
        return value
