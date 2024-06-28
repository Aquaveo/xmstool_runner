"""Qt delegate with a validator for edit fields."""
# 1. Standard python modules

# 2. Third party modules
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLineEdit, QStyledItemDelegate

# 3. Aquaveo modules

# 4. Local modules
from xms.guipy.validators.number_corrector import NumberCorrector

__copyright__ = "(C) Copyright Aquaveo 2019"
__license__ = "All rights reserved"


class EditFieldValidator(QStyledItemDelegate):
    """A combobox delegate."""
    def __init__(self, validator, parent=None):
        """Initializes the class.

        Args:
            validator (QValidator): The edit field validator to use
            parent (Something derived from QWidget): The parent window.
        """
        super().__init__(parent)
        self.validator = validator
        self.num_corrector = NumberCorrector(self)

    def createEditor(self, parent, option, index):  # noqa: N802
        """Creates the combobox and populates it.

        Args:
            parent (QWidget): The parent.
            option (QStyleOptionViewItem): The option
            index (QModelIndex): The index

        Returns:
            (QWidget)
        """
        edit = QLineEdit(parent)
        edit.setValidator(self.validator)
        edit.installEventFilter(self.num_corrector)
        return edit

    def setEditorData(self, editor, index):  # noqa: N802
        """Sets the data to be displayed and edited by the editor from the data model item specified by the model index.

        Args:
            editor (QWidget): The editor.
            index (QModelIndex): The index.
        """
        if not editor:
            return
        current_data = index.data(Qt.DisplayRole)
        editor.setText(str(current_data))

    def setModelData(self, editor, model, index):  # noqa: N802
        """Gets data from the editor widget and stores it in the specified model at the item index.

        Args:
            editor (QWidget): The editor.
            model (QAbstractItemModel): The model.
            index (QModelIndex): The index
        """
        if not editor:
            return
        model.setData(index, editor.text(), Qt.EditRole)
