"""Base class for XMS Python dialogs."""
# 1. Standard python modules
import sys

# 2. Third party modules

# 3. Aquaveo modules
from xms.api.dmi import XmsEnvironment
from xms.guipy.dialogs import message_box

# 4. Local modules

# These are file globals because we think that xms_excepthook must be a file global and not a class method
fg_ignored_exceptions = []
fg_parent = None


def _exceptions_equal(a, b):
    """Compares two exceptions and returns True if they are equal.

    Seemingly identical exceptions will not just compare as equal and we would just keep adding the same thing
    multiple times. Used in my_excepthook. See https://stackoverflow.com/questions/15844131

    Args:
        a (Exception): Something derived from Exception.
        b (Exception): Something derived from Exception.
    """
    return type(a) is type(b) and a.args == b.args


def _ignoring_exception(ex):
    """Returns True if ex is an exception we're supposed to ignore.

    Args:
        ex (Exception): Something derived from Exception.

    Returns:
        _type_: _description_
    """
    for to_ignore in fg_ignored_exceptions:
        if _exceptions_equal(to_ignore, ex):
            return True


def xms_excepthook(type, value, tback):
    """Override of sys.excepthook so we can show exceptions that Qt would otherwise silently eat.

    See https://stackoverflow.com/questions/1015047/logging-all-exceptions-in-a-pyqt4-app

    Args:
        type: exception class
        value: exception instance
        tback: traceback object
    """
    if _ignoring_exception(value):
        return

    message = 'Unexpected error. Please contact tech support.'
    app_name = XmsEnvironment.xms_environ_app_name()
    # Echo the traceback to 'python_debug.log' in the XMS temp directory.
    XmsEnvironment.report_error(value, XmsEnvironment.xms_environ_debug_file())
    # Report a pretty message to the user.
    message_box.message_with_ok(parent=fg_parent, message=message, app_name=app_name, details=str(value))
    sys.__excepthook__(type, value, tback)  # call the default handler


class XmsExcepthook:
    """Class used when overriding sys.excepthook to handle exceptions that Qt hides."""
    def __init__(self, parent):
        """Initializer."""
        global fg_parent, fg_ignored_exceptions
        fg_parent = parent
        sys.excepthook = xms_excepthook  # override sys.excepthook with our own version

    def ignore_exception(self, ex):
        """Adds exception ex to the list of exceptions to ignore in xms_excepthook.

        Args:
            ex (Exception): Something derived from Exception.
        """
        # Don't add it if it's already in the list. We manually compare the exceptions because == just doesn't work
        global fg_ignored_exceptions
        for ex in fg_ignored_exceptions:
            if _exceptions_equal(ex, ex):
                return
        fg_ignored_exceptions.append(ex)
