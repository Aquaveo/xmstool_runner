"""TableWithToolBar class."""

__copyright__ = "(C) Copyright Aquaveo 2022"
__license__ = "All rights reserved"

# 1. Standard python modules
from pathlib import Path

# 2. Third party modules
import pandas as pd
from PySide6.QtCore import QItemSelectionModel, QModelIndex, Qt, Signal
from PySide6.QtGui import QDoubleValidator
from PySide6.QtWidgets import QWidget

# 3. Aquaveo modules
from xms.api.dmi import XmsEnvironment
from xms.guipy.delegates.check_box_no_text import CheckBoxNoTextDelegate
from xms.guipy.delegates.edit_field_validator import EditFieldValidator
from xms.guipy.delegates.file_selector_delegate import FileSelectorButtonDelegate
from xms.guipy.delegates.qx_cbx_delegate import QxCbxDelegate
from xms.guipy.delegates.spin_box_delegate import SpinBoxDelegate
from xms.guipy.models.qx_pandas_table_model import QxPandasTableModel
from xms.guipy.widgets import widget_builder
from xms.guipy.widgets.table_with_tool_bar_ui import Ui_table_with_toolbar
from xms.tool_core.table_definition import (
    ChoicesColumnType, FloatColumnType, InputFileColumnType, IntColumnType, StringColumnType, TableDefinition
)


class TableWithToolBar(QWidget):
    """QxTableView with a tool bar."""

    # Shorter variable names for these icons
    ADD_SVG = ':/resources/icons/row-add.svg'
    INSERT_SVG = ':/resources/icons/row-insert.svg'
    DELETE_SVG = ':/resources/icons/row-delete.svg'
    MOVE_UP = ':/resources/icons/row-up.svg'
    MOVE_DOWN = ':/resources/icons/row-down.svg'

    # Signals
    data_changed = Signal(QModelIndex, QModelIndex)
    rows_inserted = Signal(QModelIndex, int, int)
    rows_removed = Signal(QModelIndex, int, int)

    def __init__(self, parent=None) -> None:
        """Initializes the class.

        We only take parent here so that you can use it in a .ui file via a promoted widget. See setup() method.

        Args:
            parent (QWidget): Parent window.
        """
        super().__init__(parent)
        self.ui = Ui_table_with_toolbar()
        self.ui.setupUi(self)

        self._table_def = None
        self._actions = None

    def setup(self, table_definition: TableDefinition, df: pd.DataFrame):
        """Initializes the class.

        Args:
            table_definition (TableDefinition): Defines the column types.
            df(pandas.DataFrame): The data as a pandas DataFrame.
        """
        self._table_def = table_definition
        widget_builder.style_table_view(self.ui.table)
        self._add_data_to_table(df)
        self._hide_columns()
        self._add_delegates()
        self._adjust_column_sizes()
        self._add_tool_tips()
        _setup_table_context_menus(self.ui.table, self._on_index_column_click, self._on_right_click)
        self._setup_toolbar()
        self._setup_for_fixed_row_count()
        self.ui.table.selectionModel().selectionChanged.connect(self._enable_toolbar)
        self._enable_toolbar()

    def get_values(self) -> pd.DataFrame:
        """Returns a copy of the values in the table as a pandas DataFrame."""
        return self.ui.table.model().data_frame.copy()

    def set_values(self, values: pd.DataFrame):
        """Sets up the table with the values and the existing table definition (hopefully they're compatible)."""
        self.setup(table_definition=self._table_def, df=values)

    def _add_data_to_table(self, df: pd.DataFrame) -> None:
        """Adds data to the table.

        Args:
            df(pandas.DataFrame): The data as a pandas DataFrame.
        """
        if df is None:
            df = self._table_def.to_pandas()  # Create an empty dataframe with the appropriate columns

        model = QxPandasTableModel(df)
        self.ui.table.setModel(model)

        # Set other model stuff
        table_def = self._table_def  # for short
        model.set_default_values({col_type.header: col_type.default for col_type in table_def.column_types})
        model.set_read_only_columns({i for i, col_type in enumerate(table_def.column_types) if not col_type.enabled})
        model.dataChanged.connect(self._on_data_changed)
        model.rowsInserted.connect(self._on_rows_inserted)
        model.rowsRemoved.connect(self._on_rows_removed)

    def _on_data_changed(self, top_left: QModelIndex, bottom_right: QModelIndex) -> None:
        """Called when the model sends the dataChanged signal.

        Args:
            top_left (QModelIndex): Top left of range modified.
            bottom_right (QModelIndex): Bottom right of range modified.
        """
        self.data_changed.emit(top_left, bottom_right)

    def _on_rows_inserted(self, parent: QModelIndex, first: int, last: int) -> None:
        """Called when the model sends the rowsInserted signal.

        Args:
            parent: The parent index.
            first: New items are between first and last inclusive.
            last: New items are between first and last inclusive.
        """
        self.rows_inserted.emit(parent, first, last)

    def _on_rows_removed(self, parent: QModelIndex, first: int, last: int) -> None:
        """Called when the model sends the rowsRemoved signal.

        Args:
            parent: The parent index.
            first: Removed items are between first and last inclusive.
            last: Removed items are between first and last inclusive.
        """
        self.rows_removed.emit(parent, first, last)

    def _create_data_frame(self, values) -> pd.DataFrame:
        """Returns a new DataFrame from the information in and values.

        Args:
            values: Table values as a 2D list.

        Returns:
            (pandas.DataFrame): The dataframe.
        """
        # Create dict to pass to DataFrame constructor by combining column headers with list of column values
        dataframe_dict = {}
        for index, column_type in enumerate(self._table_def.column_types):
            dataframe_dict[column_type.header] = values[index] if index < len(values) else []

        df = pd.DataFrame(dataframe_dict)
        df.index += 1
        return df

    def _hide_columns(self):
        """Hides columns if necessary."""
        for i, column in enumerate(self._table_def.column_types):
            if isinstance(column, ChoicesColumnType):
                self.ui.table.setColumnHidden(i, True)

    def _add_delegates(self) -> None:
        """Creates the column delegates using the column types."""
        check_box_columns = set()
        for col_idx, column_type in enumerate(self._table_def.column_types):
            delegate = None
            if isinstance(column_type, StringColumnType) and column_type.choices:
                delegate = QxCbxDelegate(self)
                if isinstance(column_type.choices, int):
                    delegate.set_choices_column(column_type.choices, self.ui.table.model())
                else:
                    delegate.set_strings(column_type.choices)
                self.ui.table.model().set_combobox_column(col_idx, column_type.choices)
            elif isinstance(column_type, IntColumnType):
                if column_type.spinbox:
                    delegate = SpinBoxDelegate(self, minimum=column_type.low, maximum=column_type.high)
                elif column_type.checkbox:
                    delegate = CheckBoxNoTextDelegate(self)
                    check_box_columns.add(col_idx)
            elif isinstance(column_type, FloatColumnType):
                validator = QDoubleValidator(bottom=column_type.low, top=column_type.high, parent=self)
                delegate = EditFieldValidator(validator, self)
            elif isinstance(column_type, InputFileColumnType):
                project_file = XmsEnvironment.xms_environ_project_path()
                project_dir = Path(project_file).parent if project_file else ''
                delegate = FileSelectorButtonDelegate(
                    proj_dir=project_dir, caption='Select File', parent=self, file_filters=column_type.file_filter
                )
            else:
                pass  # TODO: I only did what I needed. Feel free to expand this here. -MJK

            if delegate:
                self.ui.table.setItemDelegateForColumn(col_idx, delegate)

        if check_box_columns:
            self.ui.table.model().set_checkbox_columns(check_box_columns)

    def _adjust_column_sizes(self) -> None:
        """Tries to adjust column sizes appropriately."""
        self.ui.table.resizeColumnsToContents()
        self.ui.table.horizontalHeader().setStretchLastSection(True)
        self.ui.table.adjustSize()  # Seems to be necessary

    def _add_tool_tips(self) -> None:
        """Adds tool tips to the column headers."""
        tool_tips_dict = {index: column_type.tool_tip for index, column_type in enumerate(self._table_def.column_types)}
        self.ui.table.model().set_horizontal_header_tooltips(tool_tips_dict)

    def _setup_toolbar(self) -> None:
        """Adds buttons to the toolbar."""
        self.ui.tool_bar.clear()
        button_list = []
        if self._table_def.fixed_row_count is None:
            button_list.append([self.ADD_SVG, 'Add Row', self._on_btn_add])
            button_list.append([self.INSERT_SVG, 'Insert Row', self._on_btn_insert])
            button_list.append([self.DELETE_SVG, 'Delete Row', self._on_btn_delete])
        button_list.append([self.MOVE_UP, 'Move Up', self._on_btn_up])
        button_list.append([self.MOVE_DOWN, 'Move Down', self._on_btn_down])
        self._actions = widget_builder.setup_toolbar(self.ui.tool_bar, button_list)

    def _setup_for_fixed_row_count(self):
        """Sets up the table if it's supposed to have a fixed number of rows."""
        if self._table_def.fixed_row_count is None:
            return

        diff = self._table_def.fixed_row_count - self.ui.table.model().rowCount()
        if diff == 0:
            return
        elif diff < 0:
            diff = abs(diff)
            self.ui.table.model().removeRows(row=self.ui.table.model().rowCount() - diff, count=diff)
        else:
            self.ui.table.model().insertRows(row=self.ui.table.model().rowCount(), count=diff)  # add at bottom

        self._enable_toolbar()

    def _on_index_column_click(self, point) -> None:
        """Called on a right-click event in the index column (vertical header).

        Args:
            point (QPoint): The point clicked
        """
        row = self.ui.table.verticalHeader().logicalIndexAt(point)
        self.ui.table.selectRow(row)
        menu_list = [
            ['copy', 'Copy', self.ui.table.on_copy],
            ['paste', 'Paste', self.ui.table.on_paste],
        ]
        if self._table_def.fixed_row_count is None:
            menu_list.extend(
                [['row-insert', 'Insert', self._on_btn_insert], ['row-delete', 'Delete', self._on_btn_delete]]
            )
        menu = widget_builder.setup_context_menu(self, menu_list)
        menu.popup(self.ui.table.viewport().mapToGlobal(point))

    def _on_right_click(self, point) -> None:
        """Slot called when user right-clicks in the table.

        Args:
            point(QPoint): The point clicked.
        """
        # row = self.ui.table_view.logicalIndexAt(point)
        menu_list = [['copy', 'Copy', self.ui.table.on_copy], ['paste', 'Paste', self.ui.table.on_paste]]
        menu = widget_builder.setup_context_menu(self, menu_list)
        menu.popup(self.ui.table.viewport().mapToGlobal(point))

    def _get_unique_sorted_selected_rows(self) -> list[int]:
        """Returns the set of selected row numbers (0-based), in order from least to greatest."""
        selected_list = self.ui.table.selectedIndexes()
        return sorted(list({index.row() for index in selected_list}))

    def _reselect_rows(self, selected_rows: list[int]) -> None:
        """Selects the rows in the table that were selected before as indicated by selected_rows.

        Args:
            selected_rows(list[int]): List of rows.
        """
        for row in selected_rows:
            if row >= self.ui.table.model().rowCount():
                row = self.ui.table.model().rowCount() - 1
            idx = self.ui.table.model().createIndex(row, 0)
            flags = QItemSelectionModel.ClearAndSelect | QItemSelectionModel.Rows
            self.ui.table.selectionModel().select(idx, flags)

    def _move_row(self, up, selected_row, selected_column):
        """Moves a row up or down.

        Note: This implementation only works with DataFrames that have a 1-based sequential integer Index. If your
        DataFrame is not structured this way, you will need to override this method.

        Args:
            up (bool): True if moving up, else False
            selected_row (int): Selected row.
            selected_column (int): Selected column.
        """
        source_row = selected_row
        source_idx = source_row + 1  # Assuming a 1-based sequential integer pandas.Index
        dest_row = source_row - 1 if up else source_row + 1
        dest_idx = dest_row + 1  # Assuming a 1-based sequential integer pandas.Index

        self.ui.table.model().swap_rows(source_idx, dest_idx, source_row, dest_row)

        # Update the selection
        new_index = self.ui.table.model().index(dest_row, selected_column)
        self.ui.table.selectionModel().setCurrentIndex(
            new_index, QItemSelectionModel.SelectCurrent | QItemSelectionModel.Clear | QItemSelectionModel.Rows
        )

    def _on_btn_up(self) -> None:
        """Moves the row up."""
        selected_rows = self._get_unique_sorted_selected_rows()
        if len(selected_rows) == 1 and selected_rows[0] > 0:
            selected_list = self.ui.table.selectedIndexes()
            self._move_row(up=True, selected_row=selected_list[0].row(), selected_column=selected_list[0].column())

    def _on_btn_down(self) -> None:
        """Moves the row down."""
        selected_rows = self._get_unique_sorted_selected_rows()
        if len(selected_rows) == 1 and selected_rows[0] < self.ui.table.model().rowCount() - 1:
            selected_list = self.ui.table.selectedIndexes()
            self._move_row(up=False, selected_row=selected_list[0].row(), selected_column=selected_list[0].column())

    def _on_btn_insert(self) -> None:
        """Called when the Insert button is clicked. Inserts rows in the table."""
        selected_rows = self._get_unique_sorted_selected_rows()
        if _rows_are_contiguous(selected_rows):
            self.ui.table.model().insertRows(row=selected_rows[0], count=len(selected_rows))
        else:
            for row in reversed(selected_rows):
                self.ui.table.model().insertRows(row=row, count=1)
        self._reselect_rows(selected_rows)

    def _on_btn_add(self) -> None:
        """Called when the Add button is clicked."""
        selected_rows = self._get_unique_sorted_selected_rows()
        if not selected_rows:
            self.ui.table.model().insertRows(row=self.ui.table.model().rowCount(), count=1)
        else:
            for row in reversed(selected_rows):
                self.ui.table.model().insertRows(row=row + 1, count=1)
        selected_rows = [0] if not selected_rows else [row + 1 for row in selected_rows]
        self._reselect_rows(selected_rows)
        self._enable_toolbar()

    def _on_btn_delete(self) -> None:
        """Called when the Delete button is clicked."""
        selected_rows = self._get_unique_sorted_selected_rows()
        for row in reversed(selected_rows):
            self.ui.table.model().removeRows(row=row, count=1)
        self._reselect_rows(selected_rows)
        self._enable_toolbar()

    def _enable_toolbar(self):
        """Enables and disables things."""
        selected_list = self.ui.table.selectedIndexes()
        selections_exist = len(selected_list) > 0
        selected_rows = self._get_unique_sorted_selected_rows()
        if self._table_def.fixed_row_count is None:
            self.ui.tool_bar.widgetForAction(self._actions[self.INSERT_SVG]).setEnabled(selections_exist)
            self.ui.tool_bar.widgetForAction(self._actions[self.DELETE_SVG]).setEnabled(selections_exist)
            self.ui.tool_bar.widgetForAction(self._actions[self.ADD_SVG]).setEnabled(True)
        self.ui.tool_bar.widgetForAction(self._actions[self.MOVE_UP]).setEnabled(len(selected_rows) == 1)
        self.ui.tool_bar.widgetForAction(self._actions[self.MOVE_DOWN]).setEnabled(len(selected_rows) == 1)


def _setup_table_context_menus(table, header_column_method, general_method):
    """Sets up context menus for the header column and everywhere else in the table.

    Args:
        table: The table. Something derived from QTableView.
        header_column_method: Method to call when right-clicking in the header column.
        general_method: Method to call when right-clicking anywhere else.
    """
    table.verticalHeader().setContextMenuPolicy(Qt.CustomContextMenu)
    table.verticalHeader().customContextMenuRequested.connect(header_column_method)
    table.setContextMenuPolicy(Qt.CustomContextMenu)
    table.customContextMenuRequested.connect(general_method)


def _rows_are_contiguous(unique_selected_rows):
    """Returns true if the selected rows are not contiguous."""
    if not unique_selected_rows:
        return False
    return len(unique_selected_rows) == max(unique_selected_rows) - min(unique_selected_rows) + 1
