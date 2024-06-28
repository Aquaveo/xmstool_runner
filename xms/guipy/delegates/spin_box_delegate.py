"""Qt delegate for displaying a integer QSpinBox."""

__copyright__ = "(C) Copyright Aquaveo 2019"
__license__ = "All rights reserved"

# 1. Standard python modules

# 2. Third party modules
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QSpinBox, QStyledItemDelegate

# 3. Aquaveo modules

# 4. Local modules


class SpinBoxDelegate(QStyledItemDelegate):
    """A combobox delegate."""
    def __init__(self, parent=None, minimum: int | None = None, maximum: int | None = None):
        """Initializes the class.

        Args:
            parent (Something derived from QWidget): The parent window.
            minimum (int|None): The minimum allowed value, or if none, -2147483648
            maximum (int|None): The maximum allowed value, or if none, 2147483647.
        """
        super().__init__(parent)
        self._minimum = minimum if minimum is not None else -2147483648
        self._maximum = maximum if maximum is not None else 2147483647

    def createEditor(self, parent, option, index):  # noqa: N802
        """Creates the combobox and populates it.

        Args:
            parent (QWidget): The parent.
            option (QStyleOptionViewItem): The option
            index (QModelIndex): The index

        Returns:
            (QWidget)
        """
        editor = QSpinBox(parent)
        editor.setFrame(False)
        editor.setMinimum(self._minimum)
        editor.setMaximum(self._maximum)
        return editor

    def setEditorData(self, editor, index):  # noqa: N802
        """Sets the data to be displayed and edited by the editor from the data model item specified by the model index.

        Args:
            editor (QWidget): The editor.
            index (QModelIndex): The index.
        """
        value = int(index.model().data(index, Qt.EditRole))
        editor.setValue(value)

    def setModelData(self, editor, model, index):  # noqa: N802 - should be lowercase
        """Gets data from the editor widget and stores it in the specified model at the item index.

        Args:
            editor (QWidget): The editor.
            model (QAbstractItemModel): The model.
            index (QModelIndex): The index
        """
        editor.interpretText()
        value = editor.value()
        model.setData(index, value, Qt.EditRole)

    def updateEditorGeometry(self, editor, option, index) -> None:  # noqa: N802 - should be lowercase
        """Updates the editor's geometry.

        Args:
            editor (QWidget): The editor.
            option (QStyleOptionViewItem): The option.
            index (QModelIndex): The index.
        """
        editor.setGeometry(option.rect)
