"""Qt delegate for displaying a file selector button."""
# 1. Standard python modules
import os
from pathlib import Path

# 2. Third party modules
from PySide6.QtCore import QEvent, QSize, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QFontMetrics, QPixmap
from PySide6.QtWidgets import QApplication, QPushButton, QStyle, QStyledItemDelegate, QStyleOptionToolButton

# 3. Aquaveo modules
from xms.guipy import settings
from xms.guipy.dialogs.file_selector_dialogs import get_open_filename, get_save_filename

# 4. Local modules

__copyright__ = "(C) Copyright Aquaveo 2019"
__license__ = "All rights reserved"

NULL_SELECTION = '(none selected)'


def resolve_relative_path(absolute_path, relative_path):
    """Given a path and a path that is relative to it, return the full path.

    Args:
        absolute_path (str): An absolute path.
        relative_path (str): A path relative to the absolute path.

    Returns:
        The full path to the item indicated by relative_path.
    """
    # If they give us a filename, try to get just the path
    normpath = ''
    try:
        if os.path.isabs(relative_path):  # If already absolute, just return
            return os.path.normpath(relative_path)
        if Path(absolute_path).is_file():
            absolute_path = os.path.dirname(absolute_path)
        resolved_path = os.path.join(absolute_path, relative_path.strip("'"))
        normpath = ''
        if resolved_path:
            normpath = os.path.normpath(resolved_path)
    except Exception:
        pass
    return normpath


def get_file_selector_start_dir(label_text, proj_dir):
    """Get the directory to open file browser in.

    Args:
        label_text (str): The GUI label text associated with a file selector
        proj_dir (str): Directory of the saved project if it exists. If the project has been saved, any files
            selected at the time were converted to relative paths from the project directory.

    Returns:
        (str): File or directory to open file browser in. If previously selected file, use that file/folder.
        Otherwise, use the last directory that was stored in the registry.

    """
    start_dir = proj_dir  # Default to the project directory if there is one.
    if label_text != NULL_SELECTION:  # Start in the directory of the last selected file, if there is one.
        if not os.path.isabs(label_text):  # Stored relative to the project directory.
            label_text = resolve_relative_path(proj_dir, label_text)
        # If there was a previous selection, this is most likely a filename. If you use a filename with one of the
        # open file/folder convenience methods, it will be seen as invalid and fall through to another location. For
        # the save file variety, we want the full filename because it will be selected by default. If you are using
        # this method to show a file/folder selector dialog, you need to use the versions in file_selector_dialogs.py.
        start_dir = label_text
    if not start_dir:  # If no project location and no file previously selected, look in registry
        start_dir = settings.get_file_browser_directory()
    return start_dir


def does_file_exist(file, proj_dir):
    """Determine if a file in our persistent data still exist.

    If file is not absolute, will check if relative from the project directory exists.

    Args:
       file (str): Relative or absolute file path to check the existence of
       proj_dir (str): Project path to resolve relative paths to

    Returns:
        (bool): True if the file exists

    """
    try:
        if not os.path.isabs(file):  # Convert relative to absolute
            file = resolve_relative_path(proj_dir, file)
        return os.path.exists(file)
    except Exception:
        return False


class FileSelectorButtonDelegate(QStyledItemDelegate):
    """Delegate for the file selector button column."""
    state_changed = Signal()

    def __init__(
        self, proj_dir, caption, filter_func=None, parent=None, save_file=False, file_filters='All Files (*.*)'
    ):
        """Initializes the class.

        Args:
            proj_dir (str): Path to the project save location. If one exists, will be used to convert relative
                paths.
            caption (str): Caption text for file selector dialog when button is pressed.
            filter_func (callable): If provided, will be used to set filters in file selector dialog.
                Should return a filter string appropriate for use in a Qt file dialog given a table model index.
            parent (QObject): The parent object.
            save_file (bool): True if this is for saving files.
            file_filters (str): A list of possible file filters, separated by ';;' for multiple filters.
                For example: "Images (*.png *.xpm *.jpg);;Text files (*.txt);;XML files (*.xml)".
        """
        super().__init__(parent)
        self.proj_dir = proj_dir
        self.filter_func = filter_func
        self.caption = caption
        self._save_file = save_file
        self._file_filters = file_filters

    def updateEditorGeometry(self, editor, option, index):  # noqa: N802
        """Override of QStyledItemDelegate method of same name.

        Args:
            editor (QWidget): The editor widget.
            option (QStyleOptionViewItem): The style options.
            index (QModelIndex): The index in the model.
        """
        editor.setGeometry(option.rect)

    def paint(self, painter, option, index):
        """Override of QStyledItemDelegate method of same name.

        Args:
            painter (QPainter): The painter.
            option (QStyleOptionViewItem): The style options.
            index (QModelIndex): The index in the model.
        """
        if not index.isValid():
            return
        if (index.flags() & Qt.ItemIsEditable) == 0:
            dis_brush = QBrush(option.palette.window())
            painter.setBrush(dis_brush)

        if index.flags() & QStyle.State_Selected:
            sel_brush = QBrush(option.palette.highlight())
            painter.setBrush(sel_brush)

        if index.flags() & Qt.ItemIsEnabled:
            btn = QPushButton()
            file_path = index.data(Qt.EditRole)
            if file_path and (self._save_file or does_file_exist(file_path, self.proj_dir)):
                # Using the full path makes the table ugly, even if it is a relative path from the project save
                # location. Truncate button text to filename.
                file_path = f'.../{os.path.basename(file_path)}'
                btn.setText(file_path)
            else:
                btn.setText(NULL_SELECTION)
            btn.setFixedWidth(option.rect.width())
            btn.setFixedHeight(option.rect.height())
            pix = QPixmap(option.rect.size())
            btn.render(pix)
            painter.drawPixmap(option.rect.topLeft(), pix)
        else:
            painter.fillRect(option.rect, QColor(240, 240, 240))

    def editorEvent(self, event, model, option, index):  # noqa: N802
        """Override of QStyledItemDelegate method of same name.

        Args:
            event (QEvent): The editor event that was triggered.
            model (QAbstractItemModel): The data model.
            option (QStyleOptionViewItem): The style options.
            index (QModelIndex): The index in the model.
        """
        if index.isValid() and index.flags() & Qt.ItemIsEnabled:
            if event.type() == QEvent.MouseButtonRelease:
                old_path = index.data(Qt.EditRole)
                start_dir = get_file_selector_start_dir(old_path, self.proj_dir)
                ext_filter = '*.*' if self.filter_func is None else self.filter_func(index)
                set_data = False
                if self._save_file:
                    filename = get_save_filename(
                        parent=self.parent(),
                        selected_filter=ext_filter,
                        file_filters=self._file_filters,
                        caption=self.caption,
                        start_dir=start_dir,
                    )
                    if filename:
                        set_data = True
                else:
                    filename = get_open_filename(
                        parent=self.parent(),
                        caption=self.caption,
                        file_filter=self._file_filters,
                        start_dir=start_dir,
                    )
                    if filename and os.path.isfile(filename):
                        set_data = True
                if set_data:
                    index.model().setData(index, filename)
                    self.state_changed.emit()
        return super().editorEvent(event, model, option, index)

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
        btn_opt = QStyleOptionToolButton()
        btn_opt.rect = option.rect
        btn_opt.state = option.state | QStyle.State_Enabled

        file_path = index.data(Qt.EditRole)
        file_path = f'.../{os.path.basename(file_path)}' if file_path else '(none selected)'
        btn_opt.text = file_path

        return QApplication.style().sizeFromContents(
            QStyle.CT_ToolButton, btn_opt, QSize(fm.boundingRect(file_path).width(), hint.height())
        )
