"""Methods to construct Qt Widgets for XMS Python dialogs."""
# 1. Standard python modules

# 2. Third party modules
from dateutil import parser
from PySide6.QtCore import QDateTime, Qt
from PySide6.QtGui import QAction, QFontMetrics, QIcon, QPalette, QTextCursor
from PySide6.QtWidgets import QHeaderView, QMenu

# 3. Aquaveo modules

# 4. Local modules
from xms.guipy.resources import resources_util
from xms.guipy.resources.guipy import *  # noqa: F401, F403
from xms.guipy.settings import SettingsManager
from xms.guipy.widgets.qx_table_view import QxTableView

__copyright__ = "(C) Copyright Aquaveo 2019"
__license__ = "All rights reserved"


def setup_context_menu(widget, menu_lists):
    """Sets up a context menu on the widget with the items in menu_lists.

    Args:
        widget (QWidget): Something derived from QWidget.
        menu_lists(list[list]): List of lists of icon, string, function.

    Returns:
        (QMenu): The menu.
    """
    menu = QMenu(widget)
    for item in menu_lists:
        if item[0]:
            icon_path = resources_util.get_resource_path(item[0])
            action = QAction(QIcon(icon_path), item[1], widget)
        else:
            action = QAction(item[1], widget)
        menu.addAction(action)
        action.triggered.connect(item[2])

    return menu


def setup_toolbar(toolbar, button_list):
    """Adds toolbar buttons to a toolbar and returns the created actions.

    Given a toolbar and a list of lists of base icon filenames, descriptions,
    and functions, creates tools by adding actions and returns a dictionary of
    absolute icon filenames -> actions.

    Args:
        toolbar (QToolBar): The toolbar.
        button_list(list[list]): List of lists of base icon filenames, descriptions, and functions.

    Returns:
        (dict): base icon filenames -> actions
    """
    actions = {}
    for i in range(len(button_list)):
        if not button_list[i]:
            toolbar.addSeparator()
        else:
            icon_path = button_list[i][0]
            description = button_list[i][1]
            function = button_list[i][2]
            actions[icon_path] = toolbar.addAction(QIcon(icon_path), description, function)
    return actions


def datetime_from_string(datetime_string):
    """Parses a date/time string and returns a python datetime object.

    Args:
        datetime_string:

    Returns:
        (datetime.datetime): The datetime object.
    """
    return parser.parse(datetime_string)


def qdatetime_from_string(datetime_string):
    """Parses a date/time string and returns a QDateTime datetime object.

    Args:
        datetime_string:

    Returns:
        (QDateTime): The QDateTime object.
    """
    datetime = datetime_from_string(datetime_string)
    return QDateTime.fromString(datetime.isoformat(), Qt.ISODate)


def datetime_from_string_using_qt(datetime_string):
    """Uses QDateTime to parse a date/time string and returns a python datetime object.

    We use the Python dateutil.parser and QDateTime because it works well, but
    maybe there's a better way.

    Args:
        datetime_string:

    Returns:
        (datetime.datetime): The datetime object.
    """
    q_date_time = qdatetime_from_string(datetime_string)
    return q_date_time.toPython()


def update_extents(mn, mx, value):
    """Updates and returns the minimum and maximum if value exceeds their range.

    Args:
        mn: The minimum.
        mx: The maximum.
        value: A value to consider.

    Returns:
        (tuple): tuple containing:

            mn: The minimum

            mx: The maximum
    """
    if mn is None:
        mn = mx = value
    else:
        mn = min(mn, value)
        mx = max(mx, value)
    return mn, mx


def set_textedit_height(text_edit, row_count):
    """Sets the height of a QPlainTextEdit widget to a desired number of rows.

     From https://stackoverflow.com/questions/5258665

    Args:
        text_edit (QPlainTextEdit): The QPlainTextEdit widget.
        row_count (int): The number of rows of text desired.
    """
    text_doc = text_edit.document()  # QTextDocument
    font_metrics = QFontMetrics(text_doc.defaultFont())  # QFontMetrics
    margins = text_edit.contentsMargins()  # QMargins
    height = font_metrics.lineSpacing() * row_count + (text_doc.documentMargin() + text_edit.frameWidth()) * 2 \
        + margins.top() + margins.bottom()
    text_edit.setFixedHeight(height)


def resize_columns_to_contents(table_view):
    """Resizes the columns to their contents but keeps user interactivity.

    Args:
        table_view (QTableView): The table view.
    """
    table_view.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)

    # Save column widths
    column_widths = []
    for i in range(table_view.horizontalHeader().count()):
        column_widths.append(table_view.horizontalHeader().sectionSize(i))

    table_view.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)

    # Set column widths
    for i in range(table_view.horizontalHeader().count()):
        table_view.horizontalHeader().resizeSection(i, column_widths[i])


def insert_gridlayout_rows(start, count, layout):
    """Inserts rows in the grid layout.

    From https://stackoverflow.com/questions/16987916/add-widgets-to-qfiledialog

    Args:
        start (int): Starting row.
        count (int): Number of rows to insert.
        layout: The layout.
    """
    moved_items = []
    i = 0
    while i < layout.count() > 0:
        row, column, row_span, column_span = layout.getItemPosition(i)
        if row >= start:
            qlist = [row + count, column, row_span, column_span]
            moved_items.append((layout.takeAt(i), qlist))
            i -= 1
        i += 1

    for i in range(len(moved_items)):
        layout.addItem(
            moved_items[i][0],
            moved_items[i][1][0],
            moved_items[i][1][1],
            moved_items[i][1][2],
            moved_items[i][1][3],
        )


def make_lineedit_readonly(line_edit):
    """Makes the QLineEdit appear read-only: gray background, black text.

    See https://stackoverflow.com/questions/23915700

    Args:
        line_edit: The QLineEdit
    """
    read_only_palette = line_edit.palette()
    color1 = read_only_palette.color(QPalette.Window)
    color2 = read_only_palette.color(QPalette.WindowText)
    read_only_palette.setColor(QPalette.Base, color1)
    read_only_palette.setColor(QPalette.Text, color2)
    line_edit.setReadOnly(True)
    line_edit.setPalette(read_only_palette)


def replace_widgets(layout, old_widget, new_widget):
    """Replaces a widget with another one.

    Args:
        layout (QLayout): The layout containing the button.
        old_widget: The old widget.
        new_widget: The new widget.
    """
    old_index = layout.indexOf(old_widget)
    b = layout.takeAt(old_index)
    layout.insertWidget(old_index, new_widget)
    b.widget().deleteLater()


def fill_edt_with_file(file_name, widget, header):
    """Fills a plain text widget with the contents of a file.

    Args:
        file_name (str): file name
        widget (QPlainTextEdit): text edit
        header (str): header for the data in the edit
    """
    widget.appendPlainText(header)
    if file_name:
        with open(file_name, 'r') as file:
            txt = file.read().replace(' ', '\t')
            widget.appendPlainText(txt)
    widget.setReadOnly(True)
    widget.moveCursor(QTextCursor.Start)


def style_table_view(table_view):
    """Sets the table with the stylesheets we like.

    This is deprecated. Use style_table instead.

    Args:
        table_view (QTableView): The table.
    """
    style_table(table_view)


def style_table(table):
    """Sets the table (QTableView or QTableWidget) with the stylesheets we like.

    This is deprecated. Use style_table instead.

    Args:
        table (QTableView | QTableWidget): The table.
    """
    table.setMinimumHeight(150)  # I just think this looks better
    corner_style = 'QTableView QTableCornerButton::section {' \
                   ' border-top: 0px solid lightgrey;' \
                   ' border-bottom: 1px solid lightgrey;' \
                   ' border-right: 1px solid lightgrey;' \
                   ' border-left: 0px solid lightgrey;}'
    table.setStyleSheet(corner_style)
    h_style = 'QHeaderView::section {' \
              ' border-top: 0px solid lightgrey;' \
              ' border-bottom: 1px solid lightgrey;' \
              ' border-right: 1px solid lightgrey;' \
              ' border-left: 0px solid lightgrey; }'
    v_style = 'QHeaderView::section {' \
              ' border-top: 0px solid lightgrey;' \
              ' border-bottom: 1px solid lightgrey;' \
              ' border-right: 1px solid lightgrey;' \
              ' border-left: 0px solid lightgrey;' \
              ' padding-left: 4px;' \
              ' padding-right: 0px; }'
    table.horizontalHeader().setStyleSheet(h_style)
    table.verticalHeader().setStyleSheet(v_style)


def new_styled_table_view():
    """Returns a new QxTableView with the stylesheets we like.

    Returns:
        See description.
    """
    table_view = QxTableView()
    style_table_view(table_view)
    return table_view


def style_splitter(splitter):
    """Style a splitter widget the way we like.

    Args:
        splitter (QSplitter): The splitter widget to style
    """
    splitter.setChildrenCollapsible(False)
    splitter.setStyleSheet(
        'QSplitter::handle:horizontal { background-color: lightgrey; }'
        'QSplitter::handle:vertical { background-color: lightgrey; }'
    )


def save_splitter_geometry(splitter, package_name, dialog_name):
    """Save the current position of a splitter when a dialog closes.

    Args:
        splitter (QSplitter): The splitter widget whose geometry will be saved
        package_name (str): Name of the package, used for building registry key
        dialog_name (str): Name of the dialog, used to build registry key. If you have multiple splitters, you
            will need to generate a unique one of these for each.
    """
    settings = SettingsManager()
    settings.save_setting(package_name, f'{dialog_name}.splitter', splitter.sizes())


def restore_splitter_geometry(splitter, package_name, dialog_name):
    """Restore the position of the splitter when a dialog opens.

    Args:
        splitter (QSplitter): The splitter widget whose geometry will be saved
        package_name (str): Name of the package, used for building registry key
        dialog_name (str): Name of the dialog, used to build registry key. If you have multiple splitters, you
            will need to generate a unique one of these for each.
    """
    settings = SettingsManager()
    splitter_reg = settings.get_setting(package_name, f'{dialog_name}.splitter')
    if not splitter_reg:
        return
    splitter_sizes = [int(size) for size in splitter_reg]
    splitter.setSizes(splitter_sizes)
