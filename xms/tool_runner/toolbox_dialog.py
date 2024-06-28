"""Toolbox dialog."""
import os
from pathlib import Path
import sys
from typing import Optional, Tuple

from PySide6.QtCore import QItemSelection, QPoint, QSortFilterProxyModel, Qt
from PySide6.QtGui import QIcon, QStandardItem, QStandardItemModel
from PySide6.QtWidgets import (QAbstractItemDelegate, QAbstractItemView, QApplication, QDialog, QFileDialog,
                               QGridLayout, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QMenu, QPushButton,
                               QSizePolicy, QSpacerItem, QTabWidget, QTreeView, QVBoxLayout, QWidget)

from xms.guipy.dialogs.message_box import message_with_ok
from xms.tool_core import DataHandler

from xms.tool_runner.plotting import DatasetPlotWindow, get_dataset_plot_info
from xms.tool_runner.toolbox_history import string_matches_search, ToolboxHistory
from xms.tool_runner.toolbox_tools import ToolboxTools


windows = []


def resource_path(resource_file: str) -> str:
    """
    Convenience method for getting the full path to a resource file.

    Args:
        resource_file: Relative path of resource file (e.g. ':/resources/icons/add.svg')

    Returns:
        The full path to the resource file.
    """
    path = os.path.join(os.path.dirname(__file__), 'toolbox_icons', resource_file)
    return path


class QTreeViewWithEditor(QTreeView):
    """Tree view widget with editor."""

    def __init__(self, parent=None):
        """
        Initializes the object.

        Args:
            parent: The parent widget. Defaults to None.
        """
        super().__init__(parent)

    def closeEditor(self, editor, hint):  # noqa: N802
        """
        Handle closing of the editor widget.

        Args:
            editor: The editor widget being closed.
            hint: The hint specifying the reason for closing the editor.
        """
        if hint != QAbstractItemDelegate.EndEditHint.RevertModelCache:
            pass
            # TODO: handle editing history item.
            # selected = self.selectionModel().selectedIndexes()
            # if selected:
            #     uuid = selected[0].data(Qt.UserRole + 1)
            #     ToolboxHistory.set_note(
            #         uuid, selected[0].data(Qt.DisplayRole)
            #     )
        super().closeEditor(editor, hint)


class QDlgToolbox(QDialog):
    """Toolbox dialog with tool and history tabs."""

    def __init__(self, parent=None):
        """
        Initializes the toolbox dialog.

        Args:
            parent: The parent widget of the dialog. Defaults to None.
        """
        super().__init__(parent)
        self.data_handler = None
        self.new_history_selection = False
        self.color_map = 'magma'
        self.setup_ui()

        self.search_string_active = False
        self.tool_model = QStandardItemModel(0, 1, self)
        self.search_tool_model = QStandardItemModel(0, 1, self)
        self.proxy_model_tool = QSortFilterProxyModel(self)
        self.proxy_model_tool.setSortCaseSensitivity(Qt.CaseInsensitive)
        self.proxy_model_tool.setSourceModel(self.tool_model)
        self.tool_tree_view.setModel(self.proxy_model_tool)
        self.tool_tree_view.setHeaderHidden(True)
        self.tool_tree_view.header().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.tool_tree_view.setSortingEnabled(True)
        self.tool_tree_view.setContextMenuPolicy(Qt.CustomContextMenu)

        self.toolbox_history = ToolboxHistory()
        self.history_model = self.toolbox_history.get_model()
        self.history_tree_view.setModel(self.history_model)
        self.history_tree_view.setHeaderHidden(True)
        self.history_tree_view.header().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.history_tree_view.setSortingEnabled(False)
        self.history_tree_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.history_tree_view.setExpandsOnDoubleClick(False)
        self.history_tree_view.setEditTriggers(QAbstractItemView.EditKeyPressed)

        self.tool_tree_view.customContextMenuRequested.connect(self.tool_right_click_menu)
        self.tool_tree_view.doubleClicked.connect(self.run_tool_from_tools)
        self.tool_tree_view.selectionModel().selectionChanged.connect(self.tool_selection_changed)
        self.button_run.clicked.connect(self.on_tool_button_run)
        self.edt_search.textChanged.connect(self.search_toolbox_strings)
        self.history_tree_view.customContextMenuRequested.connect(self.history_right_click_menu)
        self.history_tree_view.doubleClicked.connect(self.run_tool_from_history)
        self.history_tree_view.selectionModel().selectionChanged.connect(self.history_selection_changed)
        self.history_tree_view.clicked.connect(self.on_history_item_clicked)
        self.button_run_history.clicked.connect(self.on_tool_button_run_from_history)
        self.button_delete_history.clicked.connect(self.on_tool_button_delete_from_history)
        self.button_notes.clicked.connect(self.on_tool_button_notes)
        self.edt_search_history.textChanged.connect(self.search_history_strings)
        self.project_button.clicked.connect(self.on_project_button_clicked)
        self.plot_button.clicked.connect(self.on_plot_button_clicked)
        self.add_tools()

    def setup_ui(self):
        """Set up the UI elements."""
        if self.objectName() == "":
            self.setObjectName("QDlgToolbox")
        self.resize(400, 416)
        self.setWindowTitle("Toolbox")
        self.vertical_layout = QVBoxLayout(self)
        self.vertical_layout.setObjectName("verticalLayout")

        self.tab_widget = QTabWidget()
        self.tools_tab = QWidget(self)
        self.tools_tab.setObjectName("m_grpTree")
        self.grid_layout = QGridLayout(self.tools_tab)
        self.grid_layout.setObjectName("m_gridLayout")
        self.txt_search = QLabel(self.tools_tab)
        self.txt_search.setObjectName("m_txtSearch")
        self.txt_search.setText("Search:")
        self.edt_search = QLineEdit(self.tools_tab)
        self.edt_search.setObjectName("m_edtSearch")
        self.tool_tree_view = QTreeView(self.tools_tab)
        self.tool_tree_view.setObjectName("m_treeView")
        self.button_run = QPushButton(self.tools_tab)
        self.button_run.setObjectName("m_buttonRun")
        self.button_run.setText("Run Tool...")
        self.button_run.setDisabled(True)
        self.plot_button = QPushButton(self.tools_tab)
        self.plot_button.setText("Plot Dataset...")
        self.plot_button.setDisabled(True)

        self.grid_layout.addWidget(self.txt_search, 0, 0, 1, 1)
        self.grid_layout.addWidget(self.edt_search, 1, 0, 1, 1)
        self.grid_layout.addWidget(self.tool_tree_view, 2, 0, 1, 1)
        self.grid_layout.addWidget(self.button_run, 3, 0, 1, 1)
        self.grid_layout.addWidget(self.plot_button, 4, 0, 1, 1)

        self.history_tab = QWidget(self)
        self.history_tab.setObjectName("m_grpHistory")
        self.grid_layout_history = QGridLayout(self.history_tab)
        self.grid_layout.setObjectName("m_gridLayoutHistory")
        self.txt_search_history = QLabel(self.history_tab)
        self.txt_search_history.setObjectName("m_txtSearchHistory")
        self.txt_search_history.setText("Search:")
        self.edt_search_history = QLineEdit(self.history_tab)
        self.edt_search_history.setObjectName("m_edtSearchHistory")
        self.history_tree_view = QTreeView(self.history_tab)
        self.history_tree_view.setObjectName("m_historyView")
        self.button_run_history = QPushButton(self.history_tab)
        self.button_run_history.setObjectName("m_buttonRunHistory")
        self.button_run_history.setText("Run Tool From History...")
        self.button_run_history.setDisabled(True)
        self.button_delete_history = QPushButton(self.history_tab)
        self.button_delete_history.setObjectName("m_buttonDeleteHistory")
        self.button_delete_history.setText("Delete...")
        self.button_delete_history.setDisabled(True)
        self.button_notes = QPushButton(self.history_tab)
        self.button_notes.setObjectName("m_buttonNotes")
        self.button_notes.setText("Notes...")
        self.button_notes.setDisabled(True)
        self.button_notes.setVisible(False)

        self.grid_layout_history.addWidget(self.txt_search_history, 0, 0, 1, 1)
        self.grid_layout_history.addWidget(self.edt_search_history, 1, 0, 1, 1)
        self.grid_layout_history.addWidget(self.history_tree_view, 2, 0, 1, 1)
        self.grid_layout_history.addWidget(self.button_run_history, 3, 0, 1, 1)
        self.grid_layout_history.addWidget(self.button_delete_history, 4, 0, 1, 1)
        self.grid_layout_history.addWidget(self.button_notes, 5, 0, 1, 1)

        self.h_layout_project_folder = QHBoxLayout()
        self.project_button = QPushButton("Project Folder...")
        self.h_layout_project_folder.addWidget(self.project_button)
        self.project_folder_label = QLabel("")
        self.h_layout_project_folder.addWidget(self.project_folder_label)

        self.vertical_layout.addLayout(self.h_layout_project_folder)
        self.vertical_layout.addWidget(self.tab_widget)
        self.tab_widget.addTab(self.tools_tab, "Tools")
        self.tab_widget.addTab(self.history_tab, "History")

        self.h_layout_btn = QHBoxLayout()
        self.h_layout_btn.setObjectName("m_hLayoutBtn")
        self.h_spcr_btn = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)

        self.h_layout_btn.addItem(self.h_spcr_btn)
        self.vertical_layout.addLayout(self.h_layout_btn)

    def add_tools(self):
        """Add the tools to the tool tree."""
        tools = ToolboxTools.get_tool_list()
        category_items = {}  # key=category name, value=model index
        for tool in tools:
            tool_program = tool['program_name']
            if tool_available(tool_program):
                category = tool['category']
                name = tool['name']
                tool_id = tool['uuid']
                description = tool['description']
                category_item = get_category_model_item(category, self.tool_model, category_items)
                tool_text = name
                tool_item = QStandardItem(tool_text)
                tool_item.setEditable(False)
                tool_item.setData(tool_id)
                tool_item.setIcon(QIcon(resource_path("toolbox_tool.svg")))
                tool_item.setToolTip(description)
                category_item.appendRow(tool_item)
        self.tool_tree_view.sortByColumn(0, Qt.AscendingOrder)

    @property
    def project_folder(self) -> str:
        """
        Get the path to the project folder.

        Returns:
            str: The project folder.
        """
        return self.project_folder_label.text()

    def set_tool_search_strings(self, search_strings: list[str]):
        """
        Set the tool search strings.

        Args:
            search_strings: The list of search strings to match against the tool names and descriptions.
        """
        tools = ToolboxTools.get_tool_list()

        search_strings_lower = [search_string.lower() for search_string in search_strings]
        self.search_tool_model.clear()
        self.search_tool_model.setColumnCount(1)
        category_items = {}  # key=category name, value=model index
        for tool in tools:
            tool_program = tool['program_name']
            if tool_available(tool_program):
                category = tool['category']
                name = tool['name']
                tool_id = tool['uuid']
                description = tool['description']
                category_item = get_category_model_item(category, self.search_tool_model, category_items)
                matches_description = string_matches_search(description, search_strings_lower)
                matches_name = string_matches_search(name, search_strings_lower)
                if matches_description or matches_name:
                    tool_text = name
                    tool_item = QStandardItem(tool_text)
                    tool_item.setEditable(False)
                    tool_item.setData(tool_id)
                    tool_item.setIcon(QIcon(resource_path("tool_item.png")))
                    tool_item.setToolTip(description)
                    category_item.appendRow(tool_item)
        self.tool_tree_view.sortByColumn(0, Qt.AscendingOrder)

    def get_tool_uuid(self, index: int) -> Tuple[bool, Optional[str]]:
        """
        Get the tool uuid for a given index.

        Args:
            index: The index of the tool in the model.

        Returns:
            (found, tool_uuid): If the tool was found, and the tool uuid or None.
        """
        item_idx = self.proxy_model_tool.mapToSource(index)
        if self.search_string_active:
            tool_item = self.search_tool_model.itemFromIndex(item_idx)
        else:
            tool_item = self.tool_model.itemFromIndex(item_idx)
        item_data = tool_item.data()
        tool_uuid = None
        found = False
        if isinstance(item_data, str):
            tool_uuid = item_data
            found = True
        return found, tool_uuid

    def get_history_uuid(self, index: int) -> str:
        """Get the UUID for a history item at a given index.

        Args:
            index (int): The index of the history item.

        Returns:
            The UUID data of the history item, or an empty string if the item does not exist.
        """
        history_item = self.history_model.itemFromIndex(index)
        uuid = ""
        if history_item:
            uuid = history_item.data()
        return uuid

    def tool_right_click_menu(self, point: QPoint):
        """
        Create and handle menu for right click in tool view.

        Args:
            point: The QPoint where the right-click event occurred.
        """
        index = self.tool_tree_view.indexAt(point)
        if index.isValid():
            _, tool_id = self.get_tool_uuid(index)
            if tool_id is None:
                return
            menu = QMenu()
            menu.addAction("Run Tool...", self.on_tool_button_run)
            menu.exec(self.tool_tree_view.mapToGlobal(point))

    def history_right_click_menu(self, point: QPoint):
        """
        Create and handle menu for right click in history view.

        Args:
            point: The QPoint where the right-click event occurred.
        """
        index = self.history_tree_view.indexAt(point)
        if index.isValid():
            uuid = self.get_history_uuid(index)
            if uuid == "":
                return
            menu = QMenu()
            menu.addAction("Run Tool From History...", self.on_tool_button_run_from_history)
            menu.addAction("Delete From History...", self.on_tool_button_delete_from_history)
            menu.addAction("Notes...", self.on_tool_button_notes)
            history_item = self.history_model.itemFromIndex(index)
            if history_item:
                if history_item.isEditable():
                    menu.addAction("Edit", self.on_edit_history_item)
            menu.exec(self.history_tree_view.mapToGlobal(point))

    def tool_selection_changed(self, selected: QItemSelection, deselected: QItemSelection) -> None:
        """
        Handle signal that the selected tool items have changed.

        Args:
            selected: The selected indices in the tool widget.
            deselected: The deselected indices in the tool widget.
        """
        if len(selected.indexes()) == 1:
            index = selected.indexes()[0]
            has_tool, _ = self.get_tool_uuid(index)
            self.button_run.setEnabled(has_tool)
        else:
            self.button_run.setEnabled(False)

    def history_selection_changed(self, selected: QItemSelection) -> None:
        """
        Handle signal that the selected history items have changed.

        Args:
            selected: The selected indices in the history widget.
        """
        self.new_history_selection = True
        if len(selected.indexes()) == 1:
            uuid = self.get_history_uuid(selected.indexes()[0])
            self.button_run_history.setEnabled(bool(uuid))
            self.button_delete_history.setEnabled(bool(uuid))
            self.button_notes.setEnabled(bool(uuid))
        else:
            self.button_run_history.setEnabled(False)
            self.button_delete_history.setEnabled(False)
            self.button_notes.setEnabled(False)

    def on_history_item_clicked(self, index: int):
        """
        Handle history item clicked.

        Args:
            index: Index of the history item.
        """
        uuid = self.get_history_uuid(index)
        if uuid and not self.new_history_selection:
            self.on_edit_history_item()
        self.new_history_selection = False

    def on_project_button_clicked(self):
        """Handle click on the select project folder button."""
        project_folder = QFileDialog.getExistingDirectory()
        self.project_folder_label.setText(project_folder)
        self.toolbox_history.read_history_file(project_folder)
        self.search_history_strings(self.edt_search_history.text())
        self.on_new_project_folder()

    def on_plot_button_clicked(self):
        """Handle click on the plot dataset button."""
        data_handler = DataHandler(file_folder=self.project_folder)
        plot_info = get_dataset_plot_info(data_handler, self.color_map)
        if plot_info is not None:
            time_step = plot_info.time_step
            self.color_map = plot_info.color_map
            window = DatasetPlotWindow(data_handler, plot_info.dataset, time_step, self.color_map)
            window.show()
            windows.append(window)

    def on_new_project_folder(self):
        """Handle change to new project folder."""
        if self.project_folder:
            self.data_handler = DataHandler(file_folder=self.project_folder)
            self.plot_button.setEnabled(True)
        else:
            self.data_handler = None
            self.plot_button.setEnabled(False)

    def enable_history_buttons(self):
        """Enable the buttons in the history tab."""
        selected = self.history_tree_view.selectionModel().selectedIndexes()
        if selected:
            self.on_history_item_clicked(selected[0])
        else:
            self.button_run_history.setEnabled(False)
            self.button_delete_history.setEnabled(False)
            self.button_notes.setEnabled(False)

    def run_tool_from_tools(self, index: int) -> None:
        """
        Runs a tool from the toolbox at the specified index.

        Args:
            index: The index of the tool in the toolbox.
        """
        has_tool, tool_uuid = self.get_tool_uuid(index)
        if not has_tool:
            return
        project_folder = self.project_folder
        if project_folder:
            run_input = ToolboxTools.get_run_input(tool_uuid)
            if run_input is not None:
                results = ToolboxTools.run_tool(run_input, project_folder)
                if results is not None:
                    self.toolbox_history.add_item(results)
                    self.toolbox_history.write_history_file(project_folder)
                    self.search_history_strings(self.edt_search_history.text())
        else:
            message_with_ok(self, "Please select the project folder.", "SMS")

    def on_tool_button_run(self):
        """Handle running a tool from the selected history item."""
        selected = self.tool_tree_view.selectionModel().selectedIndexes()
        if selected:
            self.run_tool_from_tools(selected[0])

    def on_tool_button_run_from_history(self):
        """Handle running a tool from the selected history item."""
        selected = self.history_tree_view.selectionModel().selectedIndexes()
        if selected:
            self.run_tool_from_history(selected[0])

    def on_tool_button_delete_from_history(self):
        """Delete a tool history item."""
        selected = self.history_tree_view.selectionModel().selectedIndexes()
        if selected:
            # TODO: handle deleting a history item.
            self.delete_history_item(selected[0])
            self.enable_history_buttons()

    def on_edit_history_item(self):
        """Handle editing a tool history item."""
        selected = self.history_tree_view.selectionModel().selectedIndexes()
        if selected:
            history_item = self.history_model.itemFromIndex(selected[0])
            if history_item:
                if history_item.isEditable():
                    self.history_tree_view.edit(selected[0])

    def on_tool_button_notes(self):
        """Handle notes right click menu item."""
        selected = self.history_tree_view.selectionModel().selectedIndexes()
        if selected:
            pass
            # TODO: Handle notes
            # uuid = self.get_history_uuid(selected[0])
            # index = self.toolbox_history.get_history_index_from_uuid(uuid)
            # description = self.toolbox_history.get_item_description(index)
            # props = []
            # pr_properties_and_notes_dialog("Notes for " + description, props, None, XmUuid(uuid),
            #                                "SearchKey_Toolbox_History_Notes")

    def search_toolbox_strings(self, search_strings):
        """
        Filters the tools based on the provided search strings.

        Args:
            search_strings: Search strings used to filter the tools.
        """
        filter_strings = search_strings.strip()
        if not filter_strings:
            # filter strings empty so show everything
            self.search_string_active = False
            self.proxy_model_tool = QSortFilterProxyModel(self)
            self.proxy_model_tool.setSortCaseSensitivity(Qt.CaseInsensitive)
            self.proxy_model_tool.setSourceModel(self.tool_model)
            self.tool_tree_view.setModel(self.proxy_model_tool)
            self.tool_tree_view.setHeaderHidden(True)
            self.tool_tree_view.selectionModel().selectionChanged.connect(self.tool_selection_changed)
            return

        # filter tree view to items containing strings
        self.search_string_active = True
        self.set_tool_search_strings(get_search_strings(filter_strings))
        self.proxy_model_tool = QSortFilterProxyModel(self)
        self.proxy_model_tool.setSortCaseSensitivity(Qt.CaseInsensitive)
        self.proxy_model_tool.setSourceModel(self.search_tool_model)
        self.tool_tree_view.setModel(self.proxy_model_tool)
        self.tool_tree_view.setHeaderHidden(True)
        self.tool_tree_view.expandAll()
        self.tool_tree_view.selectionModel().selectionChanged.connect(self.tool_selection_changed)

    def search_history_strings(self, search_strings: str):
        """
        Filters the history based on the provided search strings.

        Args:
            search_strings: Search strings used to filter the history.
        """
        filter_strings = search_strings.strip()
        if not filter_strings:
            # filter strings empty so show everything
            self.history_model = self.toolbox_history.get_model()
            self.history_tree_view.setModel(self.history_model)
            self.history_tree_view.setHeaderHidden(True)
            return

        # filter tree view to items containing strings
        self.toolbox_history.set_search_strings(get_search_strings(filter_strings))
        self.history_model = self.toolbox_history.history_search_model
        self.history_tree_view.setModel(self.history_model)
        self.history_tree_view.setHeaderHidden(True)
        self.history_tree_view.expandAll()
        self.enable_history_buttons()

    def delete_history_item(self, index):
        """
        Delete a tool run from the toolbox history.

        Args:
            index: The index of the tool in the history.
        """
        uuid = self.get_history_uuid(index)
        if uuid:
            self.toolbox_history.delete_item(uuid)
            self.toolbox_history.write_history_file(self.project_folder)
            self.search_history_strings(self.edt_search_history.text())

    def run_tool_from_history(self, index):
        """
        Runs a tool from the toolbox history.

        Args:
            index (int): The index of the tool in the history.
        """
        history_uuid = self.get_history_uuid(index)
        project_folder = self.project_folder
        if not project_folder:
            message_with_ok(self, "Please select the project folder.", "SMS")
            return
        if history_uuid:
            self.history_tree_view.closePersistentEditor(index)
            run_info = self.toolbox_history.get_run_input(history_uuid)
            results = ToolboxTools.run_tool(run_info, project_folder)
            if results is not None:
                self.toolbox_history.add_item(results)
                self.toolbox_history.write_history_file(project_folder)
                self.search_history_strings(self.edt_search_history.text())


def tool_available(tool_program: str) -> bool:
    """Determine if tool is available.

    Returns:
        True if the tool is available.
    """
    tool_program = tool_program.lower()
    current_program = _get_three_letter_xms_program_name().lower()
    return tool_program in ["", "xms", current_program]


def get_category_model_item(category_name, model, category_items) -> QStandardItem:
    """Get the category model item.

    Args:
        category_name: The name of the category.
        model: The model used for displaying items in the tool program.
        category_items: The dictionary containing existing category items.

    Returns:
        The category item from the category_items dictionary.
    """
    if category_name not in category_items:
        # new category so add it
        category_item = QStandardItem(category_name)
        category_item.setEditable(False)
        category_item.setIcon(QIcon(resource_path("toolbox_category.svg")))
        model.appendRow(category_item)
        category_items[category_name] = category_item
    else:
        category_item = category_items[category_name]
    return category_item


def get_search_strings(filter_string: str) -> list[str]:
    """Get a list of search strings separated by white space.

    Returns: A list of strings separated by white space.
    """
    search_strings = filter_string.split()
    return search_strings


def _get_three_letter_xms_program_name() -> str:
    """Returns the three-letter code for an XMS program name.

    Returns:
        The three-letter code for an XMS program name.
    """
    return "SMS"


def _valid_project_folder(project_folder: str) -> bool:
    """
    Check if the given project folder is a valid project folder.

    A project folder is valid if it is empty, or it has "grids", "coverages" or "rasters" folders.

    Args:
        project_folder (str): The path of the project folder to be checked.

    Returns:
        True if the project folder is valid, False otherwise.
    """
    valid = not any(Path(project_folder).iterdir())  # folder is empty
    if not valid:
        one_required = ['grids', 'coverages', 'rasters']
        valid = any(os.path.exists(os.path.join(project_folder, folder)) for folder in one_required)
    return valid


def show_toolbox():
    """Main function."""
    app = QApplication([])
    app.lastWindowClosed.connect(app.quit)
    toolbox = QDlgToolbox()
    toolbox.setModal(False)
    toolbox.show()
    windows.append(toolbox)
    sys.exit(app.exec())


if __name__ == '__main__':
    show_toolbox()
