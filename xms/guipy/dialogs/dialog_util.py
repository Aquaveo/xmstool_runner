"""Utilities common to other things in xms.guipy.dialogs."""
# 1. Standard python modules
import os
import sys

# 2. Third party modules
from PySide6.QtWidgets import QApplication

# 3. Aquaveo modules

# 4. Local modules
from xms.guipy.resources.resources_util import get_resource_path

__copyright__ = "(C) Copyright Aquaveo 2019"
__license__ = "All rights reserved"


def ensure_qapplication_exists():
    """Ensures a QApplication singleton exists. We don't have to call .exec_().

    https://stackoverflow.com/questions/11145583

    Returns:
         The QApplication singleton
    """
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


def get_xms_icon():
    """Returns the full path to the XMS window icon of the XMS process that launched this script.

    Note that this method will return empty string when the script is run outside of the XMS environment.
    """
    app_name = os.environ.get('XMS_PYTHON_APP_NAME')
    if app_name:
        return get_resource_path(f':/resources/icons/{app_name}.ico')
    return ''
