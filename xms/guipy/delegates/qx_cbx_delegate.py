"""Qt delegate for displaying a combobox."""
# 1. Standard python modules

# 2. Third party modules
from PySide6.QtCore import QModelIndex, QSize, Qt, Signal  # Fear not, Signal exists.
from PySide6.QtGui import QFontMetrics
from PySide6.QtWidgets import QApplication, QComboBox, QStyle, QStyledItemDelegate, QStyleOptionComboBox

# 3. Aquaveo modules

# 4. Local modules

__copyright__ = "(C) Copyright Aquaveo 2019"
__license__ = "All rights reserved"


class QxCbxDelegate(QStyledItemDelegate):
    """A combobox delegate."""
    state_changed = Signal(QModelIndex)
    style_changed = Signal(QSize)

    def __init__(self, parent=None):
        """Initializes the class.

        Args:
            parent (Something derived from QWidget): The parent window.
        """
        super().__init__(parent)
        self.cb = None
        self._strings = []  # List of str. The items in the combo box.
        # The next two are only used if we want the list of choices to come from another column of data in the model
        self._choices_column = None  # Column containing the list of choices
        self._model = None  # The model

    def set_strings(self, strings) -> None:
        """Sets the strings that are in the combo box.

        Args:
            strings (list[str]): The strings in the combo box.
        """
        self._strings = strings

    def get_strings(self) -> list[str]:
        """Returns the list of strings.

        Returns:
            See description.
        """
        return self._strings

    def set_choices_column(self, choices_column: int, model) -> None:
        """Sets the column which contains the list of choices.

        Args:
            choices_column: Column containing the list of choices
            model: The model.
        """
        self._choices_column = choices_column
        self._model = model

    def get_choices(self) -> list[str] | int:
        """Returns the list of strings, or, if _choices_column is not None, _choices_column.

        Returns:
            See description.
        """
        if self._choices_column is not None:
            return self._choices_column
        else:
            return self._strings

    def paint(self, painter, option, index):
        """Override the paint event.

        Args:
            painter (QPainter): The painter.
            option (QStyleOptionViewItem): The style options.
            index (QModelIndex): The index in the model.
        """
        if not index.isValid():
            return

        current_text = index.data(Qt.EditRole)
        cbx_opt = QStyleOptionComboBox()
        cbx_opt.currentText = current_text
        cbx_opt.rect = option.rect
        cbx_opt.state = option.state
        if index.flags() & Qt.ItemIsEnabled:
            cbx_opt.state |= QStyle.State_Enabled
        cbx_opt.editable = False

        QApplication.style().drawComplexControl(QStyle.CC_ComboBox, cbx_opt, painter)
        QApplication.style().drawControl(QStyle.CE_ComboBoxLabel, cbx_opt, painter)

    def sizeHint(self, option, index):  # noqa: N802
        """Help keep the size adjusted for custom painted combobox.

        Args:
            option (QStyleOptionViewItem): The style options.
            index (QModelIndex): The index in the model.

        Returns:
            (QSize): An appropriate size hint
        """
        hint = super().sizeHint(option, index)
        fm = QFontMetrics(option.font)
        cb_opt = QStyleOptionComboBox()
        cb_opt.rect = option.rect
        cb_opt.state = option.state | QStyle.State_Enabled

        hint = _size_hint_to_fit(cb_opt, fm, self._strings, hint)
        if self._choices_column is not None and self._model is not None:
            for row in range(self._model.rowCount()):
                index = self._model.index(row, self._choices_column)
                choices = self._model.data(index, role=Qt.UserRole)
                hint = _size_hint_to_fit(cb_opt, fm, choices, hint)
        return hint

    def createEditor(self, parent, option, index):  # noqa: N802
        """Creates the combobox and populates it.

        Args:
            parent (QWidget): The parent.
            option (QStyleOptionViewItem): The option
            index (QModelIndex): The index

        Returns:
            (QWidget)
        """
        self.cb = QComboBox(parent)
        if self._choices_column is not None and self._model is not None:
            index = self._model.index(index.row(), self._choices_column)
            choices = self._model.data(index, role=Qt.UserRole)
            self.cb.addItems(choices)
        else:
            self.cb.addItems(self._strings)
        self.cb.currentIndexChanged.connect(self.on_index_changed)
        return self.cb

    def setEditorData(self, editor, index):  # noqa: N802
        """Sets the data to be displayed and edited by the editor from the data model item specified by the model index.

        Args:
            editor (QWidget): The editor.
            index (QModelIndex): The index.
        """
        cb = editor
        if not cb:
            return
        current_text = index.data(Qt.EditRole)
        cb_index = cb.findText(current_text, Qt.MatchFixedString)  # Case insensitive
        if cb_index >= 0:
            cb.blockSignals(True)
            cb.setCurrentIndex(cb_index)
            cb.blockSignals(False)
            self.commitData.emit(self.cb)
            self.closeEditor.emit(self.cb)
        cb.showPopup()

    def setModelData(self, editor, model, index):  # noqa: N802
        """Gets data from the editor widget and stores it in the specified model at the item index.

        Args:
            editor (QWidget): The editor.
            model (QAbstractItemModel): The model.
            index (QModelIndex): The index
        """
        cb = editor
        if not cb:
            return

        cb_index = cb.currentIndex()
        # If it is valid, adjust the combobox
        if cb_index >= 0:
            # cb.setCurrentIndex(cb_index)
            model.setData(index, cb.currentText(), Qt.EditRole)
            self.state_changed.emit(index)

    def on_index_changed(self, index):
        """Slot to close the editor when the user selects an option.

        Args:
            index (object): unused
        """
        self.commitData.emit(self.cb)
        self.closeEditor.emit(self.cb)
        self.cb.hidePopup()
        self.cb.setParent(None)
        self.cb = None


def _size_hint_to_fit(cb_opt: QStyleOptionComboBox, fm: QFontMetrics, strings: list[str], hint: QSize) -> QSize:
    """Expands the size hint to be big enough to fit the list of strings."""
    for opt in strings:
        hint = hint.expandedTo(
            QApplication.style().sizeFromContents(
                QStyle.CT_ComboBox, cb_opt, QSize(fm.boundingRect(opt).width(), hint.height())
            )
        )
    return hint
