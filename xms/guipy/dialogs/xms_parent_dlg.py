"""Base class for XMS Python dialogs."""

# 1. Standard python modules
import os
import sys

# 2. Third party modules
from PySide6.QtCore import QObject, Qt, QThread, QTimer, Signal, Slot
from PySide6.QtGui import QIcon, QWindow
from PySide6.QtWidgets import QDialog, QWidget
try:
    from win32com.client import GetObject
except ImportError:
    GetObject = None

# 3. Aquaveo modules
from xms.api.dmi import XmsEnvironment as XmEnv
from xms.guipy.dialogs import dialog_util, message_box
from xms.guipy.dialogs.xms_excepthook import XmsExcepthook
from xms.guipy.settings import SettingsManager

# 4. Local modules


def parse_parent_window_command_args():
    """Parse the window ids of the parent XMS dialog and main XMS window. Also parses full path to window icon.

    Returns:
        (tuple(int,int,str)): HWND of parent XMS dialog, HWND of the main XMS window, full path to XMS icon
    """
    parent_hwnd = -1
    main_hwnd = -1
    if len(sys.argv) > 1:  # First argument after script is parent XMS dialog's HWND
        parent_hwnd = int(sys.argv[1])
    if len(sys.argv) > 2:  # Second argument after script is main XMS window's HWND
        main_hwnd = int(sys.argv[2])
    icon_path = dialog_util.get_xms_icon()
    return parent_hwnd, main_hwnd, icon_path


def get_xms_icon():
    """Returns the full path to the XMS window icon of the XMS process that launched this script.

    Note that this method will return empty string when the script is run outside of the XMS environment.
    """
    # This used to be defined here but I moved it to dialog_util to avoid circular imports with xms_excepthook.
    # I'm not sure what all expects it here though so I didn't delete this.
    return dialog_util.get_xms_icon()


def get_parent_window_container(hwnd):
    """Get a parent window container for child XMS Python dialogs.

    Args:
        hwnd (int): HWND of the parent hidden dialog in XMS

    Returns:
        (QWidget): See description
    """
    if hwnd < 0:
        return None
    try:
        win = QWindow.fromWinId(hwnd)
        win.setFlags(Qt.FramelessWindowHint)
        win.setModality(Qt.WindowModality.WindowModal)
        return QWidget.createWindowContainer(win)
    except Exception:
        return None


def ensure_qapplication_exists():
    """Ensures a QApplication singleton exists. We don't have to call .exec().

    https://stackoverflow.com/questions/11145583

    Returns:
         The QApplication singleton
    """
    # This used to be defined here but I moved it to dialog_util to avoid circular imports with message_box.
    # I'm not sure what all expects it here though so I didn't delete this.
    return dialog_util.ensure_qapplication_exists()


def debug_pause(message=None):
    """Opens an OK dialog.

    Useful to pause the app so that you can attach to process.

    Args:
        message (str): Message to display in the message box. If not specified, will be the running processes
            PID. This is useful since we added the process pool.
    """
    if ensure_qapplication_exists().thread() == QThread.currentThread():
        # We're running on the main thread. It's safe to pop up a dialog here.
        message = message or str(os.getpid())
        app_name = XmEnv.xms_environ_app_name()
        message_box.message_with_ok(parent=None, message=message, app_name=app_name)
    else:
        # We're not on the main thread. Probably a feedback worker thread. We need to migrate.
        DebugPauseProxy(message)


def process_id_window_title(first_part: str) -> str:
    """Returns the window title to use when debugging which shows the process ID.

    Args:
        first_part (str):  First part of the title (the regular window title).

    Returns:
        (str): See description.
    """
    return f'{first_part} - Process ID: {str(os.getpid())}'


def can_add_process_id() -> bool:
    """Returns true if we can add the process ID to the window title: in dev (version 99.99) and file hack is found."""
    if os.path.isfile('c:/temp/show_python_pid.dbg'):
        return True
        # I don't see a reason to limit this to development versions
        # version = os.environ.get('XMS_PYTHON_APP_VERSION')
        # if version and version.startswith('99.99'):
        #     return True
    return False


def add_process_id_to_window_title(dialog) -> None:
    """Adds the process ID into the window title if in dev (version 99.99) and file hack is found."""
    if can_add_process_id():
        dialog.setWindowTitle(process_id_window_title(dialog.windowTitle()))


class XmsDlg(QDialog):
    """Base class for saving and restoring window position."""
    def __init__(self, parent, dlg_name):
        """Construct the dialog.

        Args:
            parent (QObject): The dialog's Qt parent.
            dlg_name (str): Unique name for this dialog. site-packages import path would make sense.
        """
        super().__init__(parent)
        self._xms_excepthook = XmsExcepthook(parent)
        self._xms_timer = None  # Look-back poll to kill ourselves if XMS dies
        self._xms_pid = -1
        self._dlg_name = dlg_name
        self._setup_window_icons()

    def _check_xms_alive(self):
        """Kill the process if our parent XMS has died."""
        if GetObject is not None:
            wmi = GetObject('winmgmts:')
            for p in wmi.InstancesOf('win32_process'):
                if int(p.Properties_('ProcessId')) == self._xms_pid:
                    return  # Our parent XMS is still alive, continue polling.
            sys.exit(0)  # Our parent XMS is no longer running, commit suicide.

    def _ignore_exception(self, ex):
        """Adds exception ex to the list of exceptions to ignore in xms_excepthook.

        Args:
            ex (Exception): Something derived from Exception.
        """
        self._xms_excepthook.ignore_exception(ex)

    def _setup_window_icons(self):
        """Set the window icon for appropriate XMS app and disable help menu button."""
        # Disable help icon in menu bar, it is dumb and we already have button slot to handle it.
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        icon_path = dialog_util.get_xms_icon()
        if os.path.isfile(icon_path):
            self.setWindowIcon(QIcon(icon_path))

    def _restore_geometry(self):
        """Restore previous dialog size and position."""
        settings = SettingsManager()
        geometry = settings.get_setting('xmsguipy', f'{self._dlg_name}.geometry')
        if not geometry:
            return
        self.restoreGeometry(geometry)

    def _save_geometry(self):
        """Save current dialog size and position."""
        settings = SettingsManager()
        settings.save_setting('xmsguipy', f'{self._dlg_name}.geometry', self.saveGeometry())

    def showEvent(self, event):  # noqa: N802
        """Restore window position and size."""
        add_process_id_to_window_title(self)
        self._restore_geometry()
        super().showEvent(event)

    def exec(self):
        """Overload to attach a look-back poll checking if the parent XMS process is still running.

        You can use 'MANUAL' (os.environ[XmsEnvironment.ENVIRON_RUNNING_TESTS] = 'MANUAL') to avoid time out when
        testing manually instead of 'TRUE' which some dialogs use as a flag to return immediately.
        """
        running_tests = XmEnv.xms_environ_running_tests()
        if running_tests not in {'TRUE', 'ACCEPT', 'REJECT', 'CANCEL', 'MANUAL'}:  # Only poll if not running tests
            self._xms_pid = int(os.environ.get(XmEnv.ENVIRON_XMS_APP_PID, -1))
            self._xms_timer = QTimer(self)
            self._xms_timer.setInterval(10000)  # Check every 10 seconds
            self._xms_timer.timeout.connect(self._check_xms_alive)
            self._xms_timer.start()

        if running_tests in {'ACCEPT', 'TRUE'}:  # Accept immediately
            self.accept()
            return QDialog.Accepted
        elif running_tests in {'REJECT', 'CANCEL'}:  # Reject immediately
            self.reject()
            return QDialog.Rejected
        else:
            return super().exec()

    def accept(self):
        """Save window position and size."""
        self._save_geometry()
        super().accept()

    def reject(self):
        """Save window position and size."""
        self._save_geometry()
        super().reject()


class DebugPauseProxy(QObject):
    """
    A class that makes an OK dialog appear when constructed.

    If you pop up a dialog on the GUI thread, everything works fine, but trying to do it from another thread
    results in an empty dialog and hangs the whole application.

        "Qt does not support gui operations of any kind outside the main thread. Use `QThread` and send a signal back
        to the main thread with the message you want to show."

        -- ekhumoro, https://stackoverflow.com/questions/54428169/


    This proxy object is based on an answer by Tim Woocker at https://stackoverflow.com/a/68137720 and does just that.

    Constructing this on the main thread will hang the application.
    """

    called = Signal()

    def __init__(self, message):
        """
        Initialize the object.

        Args:
            message: The message to display.
        """
        super().__init__()
        self.message = message
        app = ensure_qapplication_exists()
        main_thread = app.thread()

        if QThread.currentThread() == main_thread:
            # We're going to block whichever thread constructed us and wait until the main thread does stuff.
            # If the main thread constructed us, then we'll block the main thread until the main thread does
            # stuff, which will never happen.
            #
            # Better to die promptly with a clear error than hang deep in the guts of Qt.
            raise AssertionError('Constructing DebugPauseProxy on the main thread will hang the application.')

        # Qt runs slots on the slot owner's thread by default. We want to be able to do something on the main
        # thread, so we'll move ourselves over there.
        self.moveToThread(main_thread)

        # Unsure if this matters, but it was in the source material. Setting our parent prevents us from being
        # garbage-collected at a bad time.
        self.setParent(app)

        # Use of `Qt.BlockingQueuedConnection` means whenever the signal is emitted, the emitter blocks until all the
        # slots finish. This prevents the emitting thread (which constructed this object) from continuing until the
        # slot finishes (on the main thread).
        self.called.connect(self.pause, type=Qt.BlockingQueuedConnection)
        self.called.emit()

    @Slot()
    def pause(self):
        """Pause until the user clicks OK."""
        # This is part of the implementation for debug_pause, so it's allowed to call debug_pause.
        debug_pause(self.message)  # noqa: AQU100

        # We set our parent to the main app in the constructor to avoid being garbage collected. Our job is done
        # now, so remove the parent and allow garbage-collection again.
        self.setParent(None)
