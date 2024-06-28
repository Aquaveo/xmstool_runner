"""win32 GUI utilities."""

__copyright__ = "(C) Copyright Aquaveo 2023"
__license__ = "All rights reserved"

# 1. Standard Python modules

# 2. Third party modules
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QDialog
try:
    import win32gui
except ImportError:
    win32gui = None

# 3. Aquaveo modules

# 4. Local modules


def raise_active(main_hwnd, win_cont):
    """Slot to connect to timeout signal of a QTimer for periodically bringing the Python dialog to foreground of XMS.

    Args:
        main_hwnd (int): HWND of the main XMS window
        win_cont (QWidget): Top-level XMS Python window
    """
    active_win = None
    if win32gui is not None:
        active_win = win32gui.GetActiveWindow()
    kid_id = 0
    if active_win and active_win == main_hwnd:
        kids = win_cont.children()
        for kid in kids:
            if isinstance(kid, QDialog):
                kid_id = kid.winId()
                break
        try:
            if kid_id > 0:
                win32gui.SetActiveWindow(kid_id)
        except Exception:
            pass


def create_and_connect_raise_timer(main_hwnd, win_cont):
    """Create a QTimer, connect its timeout signal to raise_active slot, and start the timer.

    Args:
        main_hwnd (int): HWND of the main XMS window
        win_cont (QWidget): Top-level XMS Python window

    Returns:
        QTimer: Timer whose timeout signal is connected to the raise_active slot
    """
    timer = QTimer()
    timer.setInterval(250)
    timer.timeout.connect(lambda: raise_active(main_hwnd, win_cont))
    timer.start()
    return timer


def raise_main_xms_window(parent_hwnd):
    """Raise the XMS parent dialog to the foreground of the XMS process.

    Args:
        parent_hwnd: Top-level XMS Python window's HWND
    """
    try:
        if win32gui is not None:
            win32gui.SetForegroundWindow(parent_hwnd)
    except Exception:
        pass
        # I disabled this log message because it shows up everywhere. Windows often throws doing this call. Most of
        # the time, it still works. Even if it doesn't the message is useless.
        # import traceback
        # f = open("debug_runner_window.txt", "w")
        # traceback.print_exception(type(ex), ex, ex.__traceback__, file=f)
        # f.close()
