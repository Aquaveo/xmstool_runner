"""Qt table model using a pandas.DataFrame for storage."""

__copyright__ = "(C) Copyright Aquaveo 2019"
__license__ = "All rights reserved"

# 1. Standard python modules

# 2. Third party modules
import numpy as np
import pandas as pd
from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt
from PySide6.QtGui import QColor

# 3. Aquaveo modules

# 4. Local modules
from xms.guipy.validators.number_corrector import NumberCorrector

NO_QMODELINDEX = QModelIndex()


class QxPandasTableModel(QAbstractTableModel):
    """Class derived from QAbstractTableModel to handle a pandas DataFrame."""
    def __init__(self, data_frame, parent=None):
        """Initializes the class.

        Args:
            data_frame (pandas.DataFrame): The pandas DataFrame.
            parent (Something derived from QWidget): The parent window.
        """
        super().__init__(parent)

        self.data_frame = data_frame
        self.read_only_columns = set()  # Columns that will be read only
        self.read_only_cells = set()  # Cells that will be read only tuples (row, col)
        self.checkbox_columns = set()  # Columns that will be displayed using a checkbox
        self.combobox_columns = {}  # Dict of column -> list of strings (or int, or dict)
        self.defaults = None
        self.show_nan_as_blank = False  # See set_show_nan_as_blank. Nan numbers are displayed as ''
        self.horizontal_header_tooltips = None

    def rowCount(self, index=NO_QMODELINDEX):  # noqa: N802
        """Returns the number of rows the model holds.

        Args:
            index (QModelIndex): The index.

        Returns:
            (int): Number of rows the model holds.
        """
        if self.data_frame is None:
            return 0
        return self.data_frame.shape[0]

    def columnCount(self, index=NO_QMODELINDEX):  # noqa: N802
        """Returns the number of columns the model holds.

        Args:
            index (QModelIndex): The index.

        Returns:
            (int): Number of columns the model holds.
        """
        if self.data_frame is None:
            return 0
        return self.data_frame.shape[1]

    def data(self, index, role=Qt.DisplayRole):  # noqa: C901
        """Depending on the index and role given, return data, or None.

        Args:
            index (QModelIndex): The index.
            role (int): The role.

        Returns:
            The data at index, or None.
        """
        shape = self.data_frame.shape
        shape_valid = 0 <= index.row() < shape[0] and 0 <= index.column() < shape[1]
        if not index.isValid() or not shape_valid:
            return None

        if role == Qt.UserRole:  # Just return the data (don't convert to string...)
            return self.data_frame.iloc[index.row(), index.column()]
        elif role == Qt.DisplayRole or role == Qt.EditRole:

            # Don't display anything in checkbox columns other than the checkboxes
            if index.column() in self.checkbox_columns:
                return ''

            value = self.data_frame.iloc[index.row(), index.column()]
            if index.column() in self.combobox_columns:  # Check for integer combobox option indices
                if np.issubdtype(type(value), np.integer):
                    s = self._match_index_to_combo_box_value(index, value)
                    if s:
                        return s

            col = self.data_frame.columns[index.column()]
            if self.data_frame[col].dtype == int:
                s = str(int(value))
                return s
            else:
                s = str(value)
                if self.data_frame[col].dtype == float:
                    if s in ['nan', 'None'] and self.show_nan_as_blank:
                        s = ''
                    else:
                        s = NumberCorrector.format_double(value)
                return s
        elif role == Qt.BackgroundRole:
            if index.column() in self.read_only_columns:
                return QColor(240, 240, 240)
            if (index.row(), index.column()) in self.read_only_cells:
                return QColor(240, 240, 240)
        elif role == Qt.CheckStateRole:
            if index.column() in self.checkbox_columns:
                i = self.data_frame.iloc[index.row(), index.column()]
                return Qt.Checked if i else Qt.Unchecked

        return None

    def setData(self, index, value, role=Qt.EditRole):  # noqa: N802, C901
        """Adjust the data (set it to <value>) depending on index and role.

        Args:
            index (QModelIndex): The index.
            value: The value.
            role (int): The role.

        Returns:
            (bool): True if successful; otherwise False.
        """
        if not index.isValid():
            return False

        if index.column() in self.read_only_columns:
            return False

        t = (index.row(), index.column())
        if t in self.read_only_cells:
            return False

        if role == Qt.EditRole or role == Qt.CheckStateRole:
            row = None
            col = None
            if len(self.data_frame.index) > index.row():
                row = self.data_frame.index[index.row()]
            if len(self.data_frame.columns) > index.column():
                col = self.data_frame.columns[index.column()]
            if row is None or col is None:
                return False

            dtype = self.data_frame[col].dtype
            is_date_time_col = is_datetime_or_timedelta_dtype(self.data_frame[col])

            if index.column() in self.checkbox_columns:
                value = 1 if value else 0  # Assume checkbox columns are integers 0 and 1
            elif index.column() in self.combobox_columns and isinstance(value, str):
                value = self._match_value_to_combo_box_item(value, index)
                if np.issubdtype(dtype, np.integer):  # Check for integer combobox option indices
                    value = self._match_value_to_combo_box_index(index, value)
            elif dtype != object:
                try:
                    if is_date_time_col:
                        value = pd.to_datetime(value)
                    else:
                        value = None if value == '' else dtype.type(value)
                except ValueError:
                    return False

            if self.data_frame.loc[row, col] != value:
                self.data_frame.at[row, col] = value
                self.dataChanged.emit(index, index)
            return True

        return False

    def headerData(self, section, orientation, role=Qt.DisplayRole):  # noqa: N802
        """Returns the data for the given role and section in the header.

        Args:
            section (int): The section.
            orientation (Qt.Orientation): The orientation.
            role (int): The role.

        Returns:
            The data.
        """
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                try:
                    return self.data_frame.columns[section]
                except IndexError:
                    return None
            elif orientation == Qt.Vertical:
                try:
                    return self.data_frame.index.tolist()[section]
                except IndexError:
                    return None
        elif role == Qt.ToolTipRole:
            if orientation == Qt.Horizontal and self.horizontal_header_tooltips:
                tool_tip = self.horizontal_header_tooltips.get(section)
                if tool_tip and not tool_tip.startswith('<span>'):
                    tool_tip = f'<span>{tool_tip}</span>'  # <span> makes it rich text causing it to wrap if needed
                return tool_tip
            else:
                return None  # I didn't implement vertical header tooltips
        else:
            return None

    def sort(self, column, order=None):
        """Sorts the model by column in the given order.

        Args:
            column (int): The column to sort.
            order (QtCore.Qt.SortOrder): The sort order.
        """
        colname = self.data_frame.columns.tolist()[column]
        self.layoutAboutToBeChanged.emit()
        self.data_frame.sort_values(colname, ascending=order != Qt.DescendingOrder, inplace=True)
        self.data_frame.reset_index(inplace=True, drop=True)
        self.data_frame.index += 1
        self.layoutChanged.emit()

    def flags(self, index):
        """Returns the item flags for the given index.

        Args:
            index (QModelIndex): The index.

        Returns:
            (int): The flags.
        """
        if not index.isValid():
            return Qt.ItemIsEnabled

        # Make it non-editable if needed
        flags = super().flags(index)
        index_column = index.column()
        if index_column in self.read_only_columns or (index.row(), index.column()) in self.read_only_cells:
            flags = flags & (~Qt.ItemIsEditable)
        else:
            flags = flags | Qt.ItemIsEditable

        # Turn on the checkbox option if needed
        if index_column in self.checkbox_columns:
            flags |= Qt.ItemIsUserCheckable
        else:
            flags &= (~Qt.ItemIsUserCheckable)

        return flags

    def set_horizontal_header_tooltips(self, tooltips):
        """Sets the tooltips for the header.

        Args:
            tooltips (dict{int, str}): Tooltips dict where int is section number.
        """
        self.horizontal_header_tooltips = tooltips

    def set_read_only_columns(self, read_only_columns):
        """Sets which columns are supposed to be read-only.

        Args:
            read_only_columns (set{int}): The read only columns.

        """
        self.read_only_columns = read_only_columns

    def set_checkbox_columns(self, checkbox_columns):
        """Sets which columns are supposed to be displayed as checkboxes.

        Args:
            checkbox_columns (set{int}): The checkbox columns.

        """
        self.checkbox_columns = checkbox_columns

    def set_combobox_column(self, column, items):
        """Tells the model that the column is a combo box delegate with the given items.

        On paste, we check the incoming data against the allowable items.

        Args:
            column (int): The column.
            items (list[str]): The combo box strings.

        """
        self.combobox_columns[column] = items

    def set_default_values(self, defaults):
        """Sets the column default values.

        Args:
            defaults(dict{str -> value}): Column names -> default values.

        """
        self.defaults = defaults

    def get_column_info(self):
        """Returns a tuple with column names and default values.

        Returns:
            (tuple): tuple containing:

                column_names (list): Column names.

                default (dict{str -> value}): Column names -> default values.
        """
        defaults = {}
        if self.defaults:
            defaults = self.defaults
        else:
            for column in self.data_frame.columns:
                defaults[column] = 0

        return list(self.data_frame.columns), defaults

    def insertRows(self, row, count, parent=None):  # noqa: N802
        """Inserts <count> rows into the model before 'row'.

         Will append to the bottom if row == row_count.

        Args:
            row (int): The row.
            count (int): The number of rows to insert.
            parent (QObject): Qt parent

        Returns:
            (bool): Returns True if rows successfully inserted; otherwise False.
        """
        row_count = self.rowCount()
        self.beginInsertRows(QModelIndex(), row, row + count - 1)
        # Get column info and create a new index
        columns, defaults = self.get_column_info()
        new_index = []
        for x in range(count):
            new_index.append(row + x + 1)
        line = pd.DataFrame(data=defaults, index=new_index, columns=columns)

        # Create the new DataFrame through concatenation
        if row < row_count:  # Insert above row
            df2 = pd.concat([self.data_frame.loc[:row], line, self.data_frame.loc[row + 1:]],
                            sort=False).reset_index(drop=True)
            df2.index = df2.index + 1  # Start index at 1, not 0
        elif self.data_frame.shape[0] == 0:  # Empty dataframe
            df2 = line
        else:  # Append to bottom
            df2 = pd.concat([self.data_frame.loc[:row], line], sort=False)

        self.data_frame = df2
        self.submit()
        last = self.createIndex(row, self.columnCount())
        self.dataChanged.emit(QModelIndex(), last)  # Needed to update the table view
        self.endInsertRows()
        return True

    def removeRows(self, row, count, parent=None):  # noqa: N802
        """Removes count rows starting with the given row from the model.

        Args:
            row (int): The row (starting at 0 regardless of DataFrame index).
            count (int): The number of rows to remove.
            parent (QObject): Qt parent

        Returns:
            (bool): Returns True if rows successfully removed; otherwise False.
        """
        self.beginRemoveRows(QModelIndex(), row, row + count - 1)
        offset = self._index_offset()

        if row == 0:
            df2 = self.data_frame.iloc[count:].reset_index(drop=True)
        else:
            df2 = pd.concat(
                [self.data_frame.loc[:row + offset], self.data_frame.loc[row + offset + count + 1:]], sort=False
            ).reset_index(drop=True)

        self.data_frame = df2
        self.data_frame.index += (offset + 1)  # Start index at 1, not 0
        self.submit()
        first = self.createIndex(row, self.columnCount())
        last = self.createIndex(row + count, self.columnCount())
        self.dataChanged.emit(first, last)  # Needed to update the table view
        self.endRemoveRows()
        return True

    def _index_offset(self) -> int:
        """Returns the offset based on whether dataframe index starts at 0 or 1.

        Returns:
            (int): See description.
        """
        index_list = self.data_frame.index.to_list()
        if index_list and isinstance(index_list[0], int):
            return index_list[0] - 1
        return 0

    def swap_rows(self, source_idx, dest_idx, source_row, dest_row):
        """Swap the data of two rows.

        Args:
            source_idx (object): The pandas Index for the row whose values should be assigned to dest_idx.
                Data type depends on structure of underlying DataFrame.
            dest_idx (object): The pandas Index for the row whose values should be assigned to source_idx.
                Data type depends on structure of underlying DataFrame.
            source_row (int): The 0-based table row index corresponding to the source_idx pandas Index.
            dest_row (int): The 0-based table row index corresponding to the dest_idx pandas Index.

        """
        if dest_row < 0 or dest_row > self.rowCount() - 1:
            return

        source_df = self.data_frame.loc[source_idx].copy()
        dest_df = self.data_frame.loc[dest_idx]
        self.data_frame.loc[source_idx] = dest_df
        self.data_frame.loc[dest_idx] = source_df
        self.submit()
        last = self.createIndex(max(source_row, dest_row), self.columnCount())
        self.dataChanged.emit(QModelIndex(), last)  # Needed to update the table view

    def _match_value_to_combo_box_item(self, value, index: QModelIndex):
        """Makes sure the value matches one of the combobox strings.

        Args:
            value (str): The value.
            index (QModelIndex): The index.

        Returns:
            The value.
        """
        combobox_strings = self.combobox_columns[index.column()]
        found = False

        # First check if we have a dict of display text to data value
        if isinstance(combobox_strings, dict):
            for data_value in combobox_strings.values():
                if value == data_value:
                    found = True
                    break
        # Next look for a match in the display text
        if not found:
            combobox_strings = self._get_combobox_strings(index)
            for string in combobox_strings:
                if value.upper() == string.upper():
                    value = string
                    found = True
                    break

        # Set it to the first string if there is not a match
        if not found and len(combobox_strings) > 0:
            value = next(iter(combobox_strings))

        return value

    def _match_index_to_combo_box_value(self, index: QModelIndex, option_index: int) -> str:
        """Returns the string at the combobox option index.

        Args:
            index: The model index.
            option_index: The combobox option index.

        Returns:
            (str): Combobox option string at index
        """
        if index.column() in self.combobox_columns:
            combobox_strings = self._get_combobox_strings(index)
            if len(combobox_strings) > option_index:
                return combobox_strings[option_index]
        return ''

    def _get_combobox_strings(self, index: QModelIndex) -> list[str]:
        """Returns the list of combobox strings given the model index.

        Args:
            index: The model index.

        Returns:
            See description.
        """
        value = self.combobox_columns[index.column()]
        if isinstance(value, int):  # value is actually the column containing the strings
            choices_index = self.createIndex(index.row(), value)
            return self.data(choices_index, role=Qt.UserRole)
        else:  # value is the list of strings
            return value

    def _match_value_to_combo_box_index(self, index: QModelIndex, value):
        """Returns the string at the combobox option index.

        Args:
            index: The model index.
            value (str): The combobox option index

        Returns:
            (int): Index of the combobox option if found, -1 otherwise
        """
        if index.column() in self.combobox_columns:
            combobox_strings = self._get_combobox_strings(index)
            try:
                return combobox_strings.index(value)
            except ValueError:
                pass
        return -1

    def set_show_nan_as_blank(self, show_nan_as_blank):
        """Sets show_nan_as_blank property. If True, nan numbers are displayed as empty strings ('').

        Args:
            show_nan_as_blank (bool): True to show nan numbers as empty strings.

        """
        self.show_nan_as_blank = show_nan_as_blank


def is_datetime_or_timedelta_dtype(column):
    """
    Check whether a Pandas table column is of type datetime or timedelta.

    Args:
        column: The column to check.

    Returns:
        Whether the column is of type datetime or timedelta.
    """
    return pd.api.types.is_datetime64_any_dtype(column) or pd.api.types.is_timedelta64_dtype(column)
