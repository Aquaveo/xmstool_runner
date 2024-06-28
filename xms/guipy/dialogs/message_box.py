"""Simple Qt message dialog."""
# 1. Standard python modules
from dataclasses import dataclass
import os

# 2. Third party modules
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QDialog, QMessageBox, QSizePolicy, QTextEdit

# 3. Aquaveo modules

# 4. Local modules
from xms.guipy.dialogs import dialog_util

__copyright__ = "(C) Copyright Aquaveo 2019"
__license__ = "All rights reserved"

MIN_DETAILS_HEIGHT = 200
MIN_DETAILS_WIDTH = 400


@dataclass
class Rectangle:
    """Simple rectangle class."""
    height: int = MIN_DETAILS_HEIGHT
    width: int = MIN_DETAILS_WIDTH


class XmsMessageBox(QMessageBox):
    """Our own class to handle resizing.

    See https://stackoverflow.com/questions/2655354/how-to-allow-resizing-of-qmessagebox-in-pyqt4
    """
    def __init__(self, parent, details_size: Rectangle | None = None, details_bottom: bool = False):
        """Initializes the class.

        Args:
            parent: The parent.
            details_size (Rectangle | None): Size of the details QTextEdit.
            details_bottom (bool): If true, the details window is scrolled to the bottom.
        """
        super().__init__(parent)
        self.setSizeGripEnabled(True)
        self._details_size = details_size
        self._details_bottom = details_bottom

    def event(self, e):
        """Handle all events to force dialog to be resizable.

        See https://stackoverflow.com/questions/2655354/how-to-allow-resizing-of-qmessagebox-in-pyqt4
        "This seems to be the best solution so far. However on every click of the "Show Details"/"Hide Details" button
        it resizes to the original small size."

        If we really care about that we could create our own dialog from scratch.

        Args:
            e: The event
        """
        result = QMessageBox.event(self, e)
        self.setMinimumHeight(0)
        self.setMaximumHeight(16777215)
        self.setMinimumWidth(0)
        self.setMaximumWidth(16777215)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        text_edit = self.findChild(QTextEdit)
        if text_edit is not None:
            min_height = self._details_size.height if self._details_size else MIN_DETAILS_HEIGHT
            min_width = self._details_size.width if self._details_size else MIN_DETAILS_WIDTH
            text_edit.setMinimumHeight(min_height)
            text_edit.setMaximumHeight(16777215)
            text_edit.setMinimumWidth(min_width)
            text_edit.setMaximumWidth(16777215)
            text_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        return result

    def _find_first_text_edit(self) -> QTextEdit | None:
        """Returns the first QTextEdit, which should be the details (hacky but necessary)."""
        text_edits = self.findChildren(QTextEdit)
        if text_edits:
            return text_edits[0]
        return None

    def _scroll_to_bottom(self) -> None:
        """Scrolls to the scroll bar to the bottom."""
        q_text_edit = self._find_first_text_edit()
        v = q_text_edit.verticalScrollBar()
        if v:
            v.setValue(v.maximum())

    def _connect_to_range_changed(self) -> None:
        """Connects to the details text edit scroll bar rangeChanged signal."""
        q_text_edit = self._find_first_text_edit()
        if q_text_edit:
            q_text_edit.verticalScrollBar().rangeChanged.connect(self._scroll_to_bottom)

    def showEvent(self, event):  # noqa: N802 - function name should be lowercase
        """Called when window is shown.

        We need to override it because it seems we cannot do the signal connection until showEvent is called.
        """
        if self._details_bottom:
            self._connect_to_range_changed()
        super().showEvent(event)

    def exec(self):
        """If testing, just accept immediately."""
        from xms.api.dmi import XmsEnvironment
        if XmsEnvironment.xms_environ_running_tests() == 'TRUE':
            self.accept()
            return QDialog.Accepted
        else:
            return super().exec()  # pragma no cover - can't hit this line if testing


def _qmessagebox_icon_from_string(icon_str):
    """Given a string, return the corresponding. QMessageBox icon (QMessageBox.Warning etc).

    Args:
        icon_str (str): ('NoIcon', 'Question', 'Information', 'Warning', 'Critical')

    Returns:
        See description.

    """
    if icon_str:  # Allow None to be passed as the icon
        qmsgbox_icons = {
            'NoIcon': QMessageBox.NoIcon,
            'Question': QMessageBox.Question,
            'Information': QMessageBox.Information,
            'Warning': QMessageBox.Warning,
            'Critical': QMessageBox.Critical
        }
        qmsgbox_icon = qmsgbox_icons.get(icon_str, QMessageBox.Warning)
    else:
        qmsgbox_icon = QMessageBox.NoIcon
    return qmsgbox_icon


def _show_details(message_box) -> None:
    """Has the details shown initially instead of waiting to show them when user hits the details button.

    See https://stackoverflow.com/questions/36083551/qmessagebox-show-details

    Args:
        message_box (QMessageBox): The message box.
    """
    for button in message_box.buttons():
        if message_box.buttonRole(button) == QMessageBox.ActionRole:
            button.click()
            break


def _set_details_fixed_width(message_box) -> None:
    """Sets the details text to be fixed width.

    See https://stackoverflow.com/questions/22519587/monospaced-detailedtext-in-qmessagebox

    I tried to see if we could pass in a QFont and translate it to a stylesheet but couldn't make it work.

    Args:
        message_box (QMessageBox): The message box.
    """
    message_box.setStyleSheet('QMessageBox QTextEdit { font-family: Courier New; font-size: 10pt}')


def _set_up_message_box(
    parent,
    message,
    app_name,
    icon,
    win_icon,
    details,
    show_details,
    details_size: Rectangle | None = None,
    details_fixed_width: bool = False,
    details_bottom: bool = False
):
    """Code common to all message box functions to set up and return the message box object.

    Args:
        parent (Something derived from QWidget): The parent window.
        message (str): Message in the dialog
        app_name (str): Name of the app to show in the window title.
        icon (str): ('NoIcon', 'Question', 'Information', 'Warning', 'Critical')
        win_icon (QIcon): The app icon to show in the window title.
        details (str): If not empty, text to show in an edit field when "Show Details" button is clicked.
        details_size (Rectangle | None): Size of the details QTextEdit.
        details_fixed_width (bool): If true, details text font is set to be fixed width
            (useful for program output).
        details_bottom (bool): If true, the details window is scrolled to the bottom.

    Returns:
        The message box object.
    """
    qmsgbox_icon = _qmessagebox_icon_from_string(icon)
    dialog_util.ensure_qapplication_exists()
    message_box = XmsMessageBox(parent, details_size, details_bottom)
    if win_icon is None:
        icon_path = dialog_util.get_xms_icon()
        win_icon = QIcon(icon_path) if os.path.isfile(icon_path) else QIcon()
    message_box.setWindowIcon(win_icon)
    message_box.setWindowTitle(app_name)
    message_box.setText(message)
    if details:
        message_box.setDetailedText(details)
    message_box.setIcon(qmsgbox_icon)
    if details and show_details:
        _show_details(message_box)
    if details_fixed_width:
        _set_details_fixed_width(message_box)
    return message_box


def message_with_ok(
    parent,
    message,
    app_name,
    icon='Warning',
    win_icon=None,
    details='',
    show_details: bool = False,
    details_size: Rectangle | None = None,
    details_fixed_width: bool = False,
    details_bottom: bool = False
):
    """Shows a simple message box with an OK button.

    If you need something more complex, use QMessageBox directly.

    Args:
        parent (Something derived from QWidget): The parent window.
        message (str): Message in the dialog
        app_name (str): Name of the app to show in the window title.
        icon (str): ('NoIcon', 'Question', 'Information', 'Warning', 'Critical')
        win_icon (QIcon): The app icon to show in the window title.
        details (str): If not empty, text to show in an edit field when "Show Details" button is clicked.
        show_details (bool): If True, details window is shown initially. Otherwise, it depends on the platform.
        details_size (Rectangle | None): Size of the details QTextEdit.
        details_fixed_width (bool): If true, details text font is set to be fixed width
            (useful for program output).
        details_bottom (bool): If true, the details window is scrolled to the bottom.
    """
    message_box = _set_up_message_box(
        parent, message, app_name, icon, win_icon, details, show_details, details_size, details_fixed_width,
        details_bottom
    )
    message_box.exec_()
    pass


def message_with_ok_cancel(
    parent,
    message,
    app_name,
    icon='Warning',
    win_icon=None,
    details='',
    show_details: bool = False,
    details_size: Rectangle | None = None,
    details_fixed_width: bool = False,
    details_bottom: bool = False
):
    """Shows a simple message box with an OK and a Cancel button.

    If you need something more complex, use QMessageBox directly.

    Args:
        parent (Something derived from QWidget): The parent window.
        message (str): Message in the dialog
        app_name (str): Name of the app to show in the window title.
        icon (str): ('NoIcon', 'Question', 'Information', 'Warning', 'Critical')
        win_icon (QIcon): The app icon to show in the window title.
        details (str): If not empty, text to show in an edit field when "Show Details" button is clicked.
        show_details (bool): If True, details window is shown initially. Otherwise, it depends on the platform.
        details_size (Rectangle | None): Size of the details QTextEdit.
        details_fixed_width (bool): If true, details text font is set to be fixed width
            (useful for program output).
        details_bottom (bool): If true, the details window is scrolled to the bottom.

    Returns:
        (bool): True on OK, False on Cancel.
    """
    message_box = _set_up_message_box(
        parent, message, app_name, icon, win_icon, details, show_details, details_size, details_fixed_width,
        details_bottom
    )
    message_box.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
    message_box.setDefaultButton(QMessageBox.Cancel)
    rv = message_box.exec_()
    return rv == QMessageBox.Ok


def message_with_n_buttons(
    parent,
    message,
    app_name,
    button_list,
    default,
    escape,
    icon='Warning',
    win_icon=None,
    details='',
    show_details: bool = False,
    details_size: Rectangle | None = None,
    details_fixed_width: bool = False,
    details_bottom: bool = False
):
    """Shows a simple message box with N number of buttons that you provide the text for.

    If you need something more complex, use QMessageBox directly.

    Args:
        parent (Something derived from QWidget): The parent window.
        message (str): Message in the dialog
        app_name (str): Name of the app to show in the window title.
        button_list (list[str]): Text for the buttons.
        default (int): 0-based index of default button.
        escape (int): 0-based index of the button clicked when user hits ESC.
        icon (str): (NoIcon, Question, Information, Warning, Critical)
        win_icon (QIcon): The app icon to show in the window title.
        details (str): If not empty, text to show in an edit field when "Show Details" button is clicked.
        show_details (bool): If True, details window is shown initially. Otherwise, it depends on the platform.
        details_size (Rectangle | None): Size of the details QTextEdit.
        details_fixed_width (bool): If true, details text font is set to be fixed width
            (useful for program output).
        details_bottom (bool): If true, the details window is scrolled to the bottom.

    Returns:
        The 0-based index of the button that was clicked.
    """
    message_box = _set_up_message_box(
        parent, message, app_name, icon, win_icon, details, show_details, details_size, details_fixed_width,
        details_bottom
    )
    buttons = []
    for text in button_list:
        buttons.append(message_box.addButton(text, QMessageBox.NoRole))
    message_box.setDefaultButton(buttons[default])
    message_box.setEscapeButton(buttons[escape])
    message_box.exec_()
    button_clicked = message_box.clickedButton()
    for index, button in enumerate(buttons):
        if button_clicked == button:
            return index
