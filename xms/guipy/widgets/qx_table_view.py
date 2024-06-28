"""QTableView implementation."""
# 1. Standard python modules
import os
import re

# 2. Third party modules
from PySide6.QtCore import QAbstractProxyModel, QModelIndex, QSize, Qt, Signal
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import QApplication, QTableView

# 3. Aquaveo modules

# 4. Local modules
from xms.guipy.delegates.qx_cbx_delegate import QxCbxDelegate
from xms.guipy.dialogs.message_box import message_with_ok

__copyright__ = "(C) Copyright Aquaveo 2019"
__license__ = "All rights reserved"


class QxTableView(QTableView):
    """QTableView implementation for use in XMS packages."""
    pasted = Signal()

    def __init__(self, parent=None):
        """Initializes the class.

        Args:
            parent (Something derived from QWidget): The parent window.
        """
        super().__init__(parent)
        self.pasting = False
        self.size_to_contents = False
        self.paste_delimiter = '\t'  # Overwrite if want to support pasting text that is not tab delimited.

        # Set this to False if you don't want to set columns with combobox delegates as combobox columns in the model.
        self.set_cbx_columns_in_model = True
        self.paste_errors = []

    def sizeHint(self):  # noqa: N802
        """Returns the size hint. Overridden to size width to contents.

        From https://stackoverflow.com/questions/6337589/qlistwidget-adjust-size-to-content

        Returns:
            See description.
        """
        if not self.size_to_contents:
            return super().sizeHint()
        else:
            s = QSize()
            s.setHeight(super().sizeHint().height())
            horz_header = self.horizontalHeader()
            count = horz_header.count()
            row_width = 0
            for i in range(count):
                if not horz_header.isSectionHidden(i):
                    row_width += horz_header.sectionSize(i)
            s.setWidth(row_width + 5)  # 5 is a buffer. Looks better
            return s

    def keyPressEvent(self, event):  # noqa: N802
        """To handle copy, paste, insert and delete.

         From https://www.walletfox.com/course/qtableviewcopypaste.php

        Args:
            event (QKeyEvent): The event.
        """
        selected_rows = self.selectionModel().selectedRows()
        # at least one entire row selected
        handled = False
        if selected_rows:
            if event.key() == Qt.Key_Insert:
                self.model().insertRows(selected_rows[0].row(), len(selected_rows))
                handled = True
            elif event.key() == Qt.Key_Delete:
                self.model().removeRows(selected_rows[0].row(), len(selected_rows))
                handled = True

        # at least one cell selected
        if not handled and self.selectedIndexes():
            if event.key() == Qt.Key_Delete:
                selected_indexes = self.selectedIndexes()
                for index in selected_indexes:
                    self.model().setData(index, '')

            elif event.matches(QKeySequence.Copy):
                self.on_copy()

            elif event.matches(QKeySequence.Paste):
                self.on_paste()
            else:
                QTableView.keyPressEvent(self, event)

    def _can_paste(self) -> bool:
        """Returns True if pasting is allowed."""
        # See if all columns are marked as read only
        model = self.model()
        if hasattr(model, 'read_only_columns') and model.read_only_columns:
            for column_index in range(model.columnCount()):
                if column_index not in model.read_only_columns:
                    return True
            return False
        return True

    def on_paste(self):
        """Pastes data from the clipboard into the selected cells."""
        if not self._can_paste():
            return

        self.pasting = True
        self.paste_errors = []
        text = QApplication.clipboard().text()
        clipboard_rows = list(filter(None, text.split("\n")))
        init_index = self.selectedIndexes()[0]
        init_row = init_index.row()
        init_col = init_index.column()

        # Insert rows if necessary
        if self.model().rowCount() < init_row + len(clipboard_rows):
            count = init_row + len(clipboard_rows) - self.model().rowCount()
            self.model().insertRows(self.model().rowCount(), count)

        selected_count = len(self.selectedIndexes())
        row_offset = 0
        if len(clipboard_rows) == 1 and selected_count > 1:
            # Paste one row into multiple selected rows by repeatedly pasting the one row
            last_index = self.selectedIndexes()[-1]
            last_row = last_index.row()
            for row in range(init_row, last_row + 1):
                self.paste_row(
                    clipboard_index=0,
                    clipboard_rows=clipboard_rows,
                    init_row=row,
                    init_col=init_col,
                    row_offset=row_offset
                )
        else:
            # Paste one or more rows into the table (doesn't matter how many are selected)
            for i in range(len(clipboard_rows)):
                self.paste_row(
                    clipboard_index=i,
                    clipboard_rows=clipboard_rows,
                    init_row=init_row,
                    init_col=init_col,
                    row_offset=row_offset
                )

        self.pasting = False
        if self.paste_errors:
            msg = 'Errors occurred when pasting data.'
            details = '\n'.join(self.paste_errors)
            self.paste_errors = []
            app_name = os.environ.get('XMS_PYTHON_APP_NAME', '')
            message_with_ok(
                parent=self.window(), message=msg, app_name=app_name, icon='Error', win_icon=None, details=details
            )
        self.model().dataChanged.emit(QModelIndex(), QModelIndex())  # Needed to update the table view
        self.pasted.emit()

    def paste_row(self, clipboard_index, clipboard_rows, init_row, init_col, row_offset):
        """Paste a row to the table.

        Args:
            clipboard_index (int): Index of row being pasted.
            clipboard_rows (list[str]): Rows being pasted.
            init_row (int): Upper left index of table row where we're pasting.
            init_col (int): Upper left index of table column where we're pasting.
            row_offset (int): Increases as hidden rows are skipped.
        """
        # Skip hidden rows
        row = init_row + clipboard_index + row_offset
        while self.isRowHidden(row):
            row_offset += 1
            row += 1

        column_contents = re.split(self.paste_delimiter, clipboard_rows[clipboard_index])
        column_offset = 0
        for j in range(len(column_contents)):

            # Skip hidden columns
            col = init_col + j + column_offset
            while self.isColumnHidden(col):
                column_offset += 1
                col += 1

            if row < self.model().rowCount() and col < self.model().columnCount():
                if not self.model().setData(self.model().index(row, col), column_contents[j]):
                    self.paste_errors.append(f'Error setting data in row: {row + 1}, column: {col + 1}')

    def on_copy(self):
        """Copies data from the selected cells to the clipboard."""
        text = ''
        tab = '\t'
        # For some reason the following crashes so we do it one at a time
        # selection_range = self.selectionModel().selection().first()
        selection_model = self.selectionModel()
        selection = selection_model.selection()
        selection_range = selection.first()
        for i in range(selection_range.top(), selection_range.bottom() + 1):
            row_contents = []
            if not self.isRowHidden(i):
                for j in range(selection_range.left(), selection_range.right() + 1):
                    if not self.isColumnHidden(j):
                        row_contents.append(self.model().index(i, j).data())
            text = text + tab.join(str(cell_contents) for cell_contents in row_contents) + '\n'
        QApplication.clipboard().setText(text)

    def setItemDelegateForColumn(self, column, delegate):  # noqa: N802
        """Override of base class version so we can handle delegates on paste.

        Args:
            column (int): The column.
            delegate: The delegate.

        """
        if self.set_cbx_columns_in_model and self.model():
            if isinstance(delegate, QxCbxDelegate):
                col = column
                local_model = self.model()
                while isinstance(local_model, QAbstractProxyModel):
                    source_idx = local_model.mapToSource(local_model.index(0, col))
                    col = source_idx.column()
                    local_model = local_model.sourceModel()
                local_model.set_combobox_column(col, delegate.get_choices())

        # Call the base class
        super().setItemDelegateForColumn(column, delegate)

    def resize_height_to_contents(self):
        """Resize the table view height based on the number of rows."""
        vert_header = self.verticalHeader()
        count = vert_header.count()
        scrollbar_height = self.horizontalScrollBar().height()
        header_height = self.horizontalHeader().height()
        row_height = 0
        for i in range(count):
            if not vert_header.isSectionHidden(i):
                row_height += vert_header.sectionSize(i)
        self.setMinimumHeight(scrollbar_height + header_height + row_height)

    def setModel(self, model) -> None:  # noqa: N802
        """Overrides QTableView setModel so that we can do some extra stuff.

        Args:
            model (QAbstractItemModel): The model.
        """
        super().setModel(model)
        self._connect_show_combo_box_popup()

    def _connect_show_combo_box_popup(self):
        """Connects the selectionChanged signal to the _show_combo_box_popup() slot."""
        if self.selectionModel():
            self.selectionModel().selectionChanged.connect(self._show_combo_box_popup)

    def _show_combo_box_popup(self, current, previous) -> None:
        """If attached to QTableView.selectionModel().selectionChanged signal, shows combo box delegate menu on click.

        We call QxTableView.edit() when a cell with a combo box is selected so the pop-up menu is shown immediately.
        See https://stackoverflow.com/questions/67431515/auto-expand-qcombobox-that-is-delegate-in-qtreeview. Otherwise
        it takes like 3 clicks to get it to show.

        You must connect the signal after setting up the model. Otherwise, QTableView.selectionModel() may be None.

        Args:
            current (QItemSelection): current index.
            previous (QItemSelection): previous index.
        """
        combo_box_delegate_columns = self._get_combo_box_delegate_columns()
        if combo_box_delegate_columns:
            indexes = current.indexes()
            if len(indexes) == 1:
                index = indexes[0]
                if index.column() in combo_box_delegate_columns:
                    self.edit(index)

    def _get_combo_box_delegate_columns(self) -> set[int] | None:
        """Returns a set of integers indicating the columns that have QxCbxDelegate delegates."""
        combo_box_delegate_columns = set()
        model = self.model()
        if model:
            for column in range(model.columnCount()):
                delegate = self.itemDelegateForColumn(column)
                if delegate and isinstance(delegate, QxCbxDelegate):
                    combo_box_delegate_columns.add(column)
        return combo_box_delegate_columns
