"""Thin wrapper of QToolBar."""
# 1. Standard python modules

# 2. Third party modules
from PySide6.QtWidgets import QToolBar

# 3. Aquaveo modules

# 4. Local modules

__copyright__ = "(C) Copyright Aquaveo 2019"
__license__ = "All rights reserved"


class ToolBar(QToolBar):
    """Class derived from QToolBar so that you can add toolbars in Qt Designer by promoting a QWidget.

    I added no new functionality to QToolBar.
    """
    def __init__(self, *args, **kwargs) -> None:
        """Initializes the class.

        Args:
            args: Arguments.
            kwargs: Keyword arguments.
        """
        super().__init__(*args, **kwargs)
