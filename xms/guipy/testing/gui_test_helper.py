"""For testing."""

# 1. Standard python libraries

# 2. Third party libraries
from PySide6.QtCore import QEventLoop, QPoint, Qt
from PySide6.QtGui import QKeySequence
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QComboBox, QLineEdit

# 3. Local libraries


class GuiTestHelper:
    """Class used to help with GUI tests."""
    @staticmethod
    def process_events(time_out=0.1):
        """Process pending application events.

        Timeout is used, because on Windows hasPendingEvents() always returns True

        Args:
            time_out (float): The maximum amount of time in seconds to wait for events.
        """
        QApplication.processEvents(QEventLoop.AllEvents, 100)

    @staticmethod
    def set_line_edit_table_cell(view, row, col, new_value, role, select_all=False, only_get=False):
        """Sets the value of a line edit in a table cell.

        Args:
            view (QTableView): The view that will be changed.
            row (int): The row of the cell in the table.
            col (int): The column of the cell in the table.
            new_value (str): The new value to set in the table cell.
            role (int): The role of the data in the model.
            select_all (bool): If True, then all of the text will be selected before entering the new text value.
            only_get (bool): If true, only get
        """
        idx_pos = GuiTestHelper.get_index_position(view, row, col)
        GuiTestHelper.click_at_view_position(view, idx_pos)
        QTest.mouseDClick(view.viewport(), Qt.MouseButton.LeftButton, pos=idx_pos)
        GuiTestHelper.process_events()
        editors = view.viewport().findChildren(QLineEdit)
        if editors:
            if select_all:
                sequence = QKeySequence(Qt.CTRL + Qt.Key_A)
                QTest.keySequence(editors[0], sequence)
            if not only_get:
                QTest.keyClicks(editors[0], new_value)
            GuiTestHelper.process_events()
            idx_pos = GuiTestHelper.get_index_position(view, 0, 0)
            idx_pos.setX(idx_pos.x() - 1)
            QTest.mouseClick(view.viewport(), Qt.MouseButton.LeftButton, pos=idx_pos)
        else:
            return None
        GuiTestHelper.process_events()
        edt_idx = view.model().index(row, col)
        edt_value = view.model().data(edt_idx, role)
        return edt_value

    @staticmethod
    def set_combo_box_table_cell(view, row, col, new_value, role, is_units=False):
        """Sets the value of a combobox in a table cell.

        Args:
            view (QTableView): The view that will be changed.
            row (int): The row of the cell in the table.
            col (int): The column of the cell in the table.
            new_value (str): The new value to set in the table cell.
            role (int): The role of the data in the model.
            is_units (bool): True if the combobox is part of a value and units delegate.
        """
        idx_pos = GuiTestHelper.get_index_position(view, row, col)
        GuiTestHelper.click_at_view_position(view, idx_pos)
        if is_units:
            QTest.mouseDClick(view.viewport(), Qt.MouseButton.LeftButton, pos=idx_pos)
            GuiTestHelper.process_events(time_out=0.5)
        editors = view.viewport().findChildren(QComboBox)
        if editors:
            if editors[0].findText(new_value) < 0:
                return None
            editors[0].setCurrentText(new_value)
            idx_pos = GuiTestHelper.get_index_position(view, 0, 0)
            idx_pos.setX(idx_pos.x() - 1)
            QTest.mouseClick(view.viewport(), Qt.MouseButton.LeftButton, pos=idx_pos)
        else:
            return None
        GuiTestHelper.process_events()
        edt_idx = view.model().index(row, col)
        edt_value = view.model().data(edt_idx, role)
        return edt_value

    @staticmethod
    def click_at_view_position(view, idx_pos):
        """Clicks the mouse at a given positions and waits for events to process.

        Args:
            view (QAbstractItemView): The view that is being clicked in (or out of).
            idx_pos (QPoint): The point location relative to the view that the mouse is clicking.
        """
        QTest.mouseClick(view.viewport(), Qt.MouseButton.LeftButton, pos=idx_pos)
        GuiTestHelper.process_events()

    @staticmethod
    def get_index_position(view, row, col):
        """Gets the point location of the given row and column in a table view.

        Args:
            view (QTableView): The table view.
            row (int): The row in the table.
            col (int): The column in the table.
        """
        row_pos = view.rowViewportPosition(row) + 1
        col_pos = view.columnViewportPosition(col) + 1
        idx_pos = QPoint(col_pos, row_pos)
        return idx_pos
