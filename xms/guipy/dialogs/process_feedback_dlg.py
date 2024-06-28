"""Dialog for printing feedback to the user during long-running operations."""
# 1. Standard python modules
import datetime
import logging
import sys
from typing import Optional

# 2. Third party modules
from PySide6.QtCore import QCoreApplication, QObject, Qt, Signal
from PySide6.QtGui import QColor, QFont, QMovie
from PySide6.QtWidgets import QApplication, QDialog, QDialogButtonBox, QWidget
from testfixtures import LogCapture

# 3. Aquaveo modules
from xms.api.dmi import XmsEnvironment as XmEnv
from xms.guipy.dialogs import windows_gui, xms_parent_dlg
from xms.guipy.dialogs.dialog_util import ensure_qapplication_exists
from xms.guipy.dialogs.feedback_thread import FeedbackThread
from xms.guipy.dialogs.process_feedback_dlg_ui import Ui_ProcessFeedbackDlg
from xms.guipy.dialogs.process_feedback_thread import ProcessFeedbackThread
from xms.guipy.dialogs.xms_parent_dlg import XmsDlg

# 4. Local modules

__copyright__ = "(C) Copyright Aquaveo 2019"
__license__ = "All rights reserved"


def extract_level(msg):
    """Looks for $XMS_LEVEL$ at end of msg, extracts it and returns the level number immediately following it as an int.

    Args:
        msg:

    Returns:
        (int): The log level.
    """
    pos = msg.find(LogEchoQtHandler.xms_level_string)
    if pos > -1:
        level = int(msg[pos + len(LogEchoQtHandler.xms_level_string):])
        return msg[:pos], level
    else:
        return msg, 20  # This shouldn't happen


class LogEchoQtHandler(logging.Handler):
    """Handler for redirecting logging module messages to dialog."""

    xms_level_string = '$XMS_LEVEL$'
    log_level_critical = 50
    log_level_error = 40
    log_level_warning = 30

    def __init__(self):
        """Construct the handler."""
        super().__init__()

    def emit(self, record):
        """Output a message."""
        levelno = record.levelno
        if record.exc_info is not None:
            # Echo traceback to 'python_debug.log' file in the XMS temp directory.
            XmEnv.report_error(record.exc_info[1], log_file=XmEnv.xms_environ_debug_file())
            record = str(record.exc_info[1])  # But only report the actual error message to the user.
        else:  # No exception info, just use default formatting for the log message.
            record = self.format(record)
        if record:
            # Embed the log level in the message. We did this after trying a few other approaches which didn't work
            # (like using a class global, defining a set_level() method, adding an arg to the write() method.
            LogEchoQSignalStream.stdout().write('%s%s%d' % (record, LogEchoQtHandler.xms_level_string, levelno))


class LogEchoQSignalStream(QObject):
    """Dummy stream for firing off echo QSignals when logging message is added."""
    _stdout = None
    _stderr = None
    logged_error = False  # Red - very bad
    logged_warning = False  # Yellow - kind of bad
    message_logged = Signal(str, int)

    def __init__(self):
        """Constuct the stream."""
        super().__init__()

    @staticmethod
    def reset_flags():
        """Reset the error and warning flags to successful state."""
        LogEchoQSignalStream.logged_error = False
        LogEchoQSignalStream.logged_warning = False

    @staticmethod
    def stdout():
        """Redirect stdout."""
        if not LogEchoQSignalStream._stdout:
            LogEchoQSignalStream._stdout = LogEchoQSignalStream()
            sys.stdout = LogEchoQSignalStream._stdout
        return LogEchoQSignalStream._stdout

    @staticmethod
    def stderr():
        """Redirect stderr."""
        if not LogEchoQSignalStream._stderr:
            LogEchoQSignalStream._stderr = LogEchoQSignalStream()
            sys.stderr = LogEchoQSignalStream._stderr
        return LogEchoQSignalStream._stderr

    def write(self, log_message):
        """Fire off a signal so the log message can be echoed.

        Args:
            log_message (str): str object containing the text to write.

        """
        if not self.signalsBlocked():
            log_message, level = extract_level(log_message)

            # If we change the format of the log messages, make sure to update this logic for detecting fatal errors.
            if level >= LogEchoQtHandler.log_level_error:
                LogEchoQSignalStream.logged_error = True
            elif level == LogEchoQtHandler.log_level_warning:
                LogEchoQSignalStream.logged_warning = True
            self.message_logged.emit(log_message, level)

    def flush(self):
        """Do nothing implementation."""
        pass

    def fileno(self):
        """Do nothing implementation."""
        return -1


class ProcessFeedbackDlg(XmsDlg):
    """
    A dialog for viewing GUI feedback during a long-running process.

    Using this requires some special boilerplate. See `run_feedback_dialog()` below for an alternative that doesn't.
    """
    def __init__(self, display_text, logger_name, worker, parent=None):
        """Initializes the class, sets up the ui.

        Args:
            display_text (dict): Text to be displayed in the GUI::

                {
                    'title': 'The dialog window title',
                    'working_prompt': 'Initial "Please wait..." message in prompt label',
                    'error_prompt': 'Prompt message to display when ERROR or CRITICAL message logged.',
                    'warning_prompt': 'Prompt message to display when WARNING message logged.',
                    'success_prompt': 'Prompt message to display when processing completes successfully.',
                    'note': 'Text in operation specific additional notes label',
                    'auto_load': 'Text for the auto load (automatically close the dialog) toggle. If empty no toggle.',
                    'log_format': '%(levelname)-8s - %(asctime)s - %(name)s - %(message)s',
                    'date_format': '%Y-%m-%d %H:%M:%S'
                    'use_colors': False,  # If True, warnings are green, errors are red and don't have ******
                }

            logger_name (str): Name of the top-level logger to echo to dialog text widget. Should match
                name of the logging module logger.
            worker (QThread): The processing worker thread. Needs to have a signal named 'processing_finished'
                that is emitted whenever the worker thread finishes its stuff. If errors occur in the worker thread, use
                the logging module to log them at ERROR or CRITICAL level. User will be notified and prompted to check
                the log output window. Catch your exceptions in the worker thread and use the logging module to log
                an ERROR or CRITICAL level message. Use logger's exception convenience method inside except clauses to
                log an ERROR level message with a nice traceback for debuggin. DEBUG, INFO, and WARNING level messages
                are echoed to the dialog's log output window, but they are not presented to the user as fatal to the
                processing operation.
            parent (Something derived from QWidget): The parent window

        """
        super().__init__(parent, 'xmsguipy.dialogs.process_feedback_dlg')
        self.ui = Ui_ProcessFeedbackDlg()
        self.ui.setupUi(self)
        self.display_text = display_text
        self._finished = False
        self.indicator = None
        self.setWindowTitle(self.display_text.get('title', 'Processing...'))
        self.worker = worker
        self.timer = None
        self.start_time = None
        self.testing = False  # Don't hang dialog if testing.
        self.log_capture = None
        self.handler = None

        # Set up the logging listener to fire off signals whenever logging module messages are logged so they can
        # be echoed to the dialog's log output window.
        self.logger = logging.getLogger(logger_name)
        self.logger.setLevel(logging.DEBUG)
        self.handler = LogEchoQtHandler()

        # Set format
        fmt = self.display_text.get('log_format', '%(levelname)s - %(asctime)s - %(name)s - %(message)s')
        datefmt = self.display_text.get('date_format', '')
        formatter = logging.Formatter(fmt, datefmt)
        formatter.default_msec_format = '%s.%03d'
        self.handler.setFormatter(formatter)
        self.ui.txt_log.setTabStopDistance(60)
        # Use a monospace font so we can print pretty tables. This one is not obnoxious and should always be installed.
        # I didn't make this a kwarg because it seems we should be consistent here.
        self.ui.txt_log.setFont(QFont('Courier'))

        self.logger.addHandler(self.handler)

        self._setup_ui()

    def _setup_ui(self):
        """Add the programmatic widgets."""
        # Disable "X" close button
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowCloseButtonHint)

        # Populate label text
        self.ui.lbl_status.setText(self.display_text.get('working_prompt', ''))
        self.ui.lbl_note.setText(self.display_text.get('note', ''))
        # Set text for auto load toggle, hide if not present.
        if 'auto_load' in self.display_text and self.display_text['auto_load']:
            self.ui.tog_auto_close.setText(self.display_text['auto_load'])
        else:
            self.ui.tog_auto_close.setCheckState(Qt.Unchecked)
            self.ui.tog_auto_close.setVisible(False)

        # Connect signal for echoing log messages
        LogEchoQSignalStream.stdout().message_logged.connect(self.on_message_logged)
        LogEchoQSignalStream.stderr().message_logged.connect(self.on_message_logged)
        # Disable OK button until we are finished mapping
        self.ui.btn_box.button(QDialogButtonBox.Ok).setEnabled(False)
        # Connect to the finished signal of the worker thread
        self.worker.processing_finished.connect(self.processing_finished)
        # Add the busy indicator label
        self.indicator = QMovie(':resources/animations/load_indicator_small.gif')
        self.ui.lbl_load_indicator.setMovie(self.indicator)
        self.indicator.start()

    def closeEvent(self, event):  # noqa: N802
        """Ignore close event while still performing operation."""
        self.logger.removeHandler(self.handler)
        if not self._finished:
            event.ignore()
        else:
            super().closeEvent(event)

    def accept(self):
        """Override the accept method."""
        self.logger.removeHandler(self.handler)
        super().accept()

    def reject(self):
        """Set flags to prevent sending data to XMS when user cancels."""
        self._finished = True  # No more work to be done
        LogEchoQSignalStream.logged_error = True  # Let calling code know data should not be sent to XMS
        self.worker.quit()  # Kill the worker
        self.logger.removeHandler(self.handler)
        super().reject()  # Close the dialog.

    def exec(self):
        """Override to start the worker thread before exec and wait on it after."""
        self.start_time = datetime.datetime.now()
        self.show()  # Make sure the dialog is visible and widgets are drawn before starting worker thread and exec
        QCoreApplication.instance().processEvents()
        if self.testing and isinstance(self.worker, ProcessFeedbackThread):
            return self._do_test_run()
        else:
            self.worker.start()
        return super().exec()

    def _do_test_run(self):
        """Run the dialog in testing mode.

        Returns:
            self.reject() or self.accept()
        """
        with LogCapture() as lc:
            my_err = None
            try:
                self.worker.do_work()
            except Exception as e:
                my_err = e
            log = [(r.levelno, r.msg) for r in lc.records]
            log_txt = f'{lc}'
        for r in log:
            self.logger.log(r[0], r[1])
        if my_err is not None:
            raise my_err
        if 'ERROR' in log_txt:
            self.reject()
            return False
        self.accept()
        return True

    def logged_error(self):
        """Returns True if an error was logged.

        Returns:
            (bool): see above
        """
        return LogEchoQSignalStream.logged_error

    def on_message_logged(self, msg, level):
        """Periodically process Qt events in GUI thread.

        Args:
            msg (str): The log message.
            level (int): The log level.
        """
        # Apply formatting
        msg, old_color, use_colors = self._format_warnings_and_errors(msg, level)
        bold, msg = self._make_bold_if_necessary(msg)

        self.ui.txt_log.append(msg)
        self.ui.txt_log.repaint()

        # Restore formatting back to normal
        if use_colors and level >= LogEchoQtHandler.log_level_warning:
            self.ui.txt_log.setTextColor(old_color)
        if bold:
            self.ui.txt_log.setFontWeight(QFont.Normal)

    def _make_bold_if_necessary(self, msg):
        """Look for keyword '$XMS_BOLD$' in message and if found, remove it, and set font weight to bold.

        Args:
            msg (str): The log message.

        Returns:
            (tuple): tuple containing:

                bold (bool): Flag indicating if font is now bold.

                msg (str): Modified log message without the '$XMS_BOLD$'
        """
        bold = False
        if '$XMS_BOLD$' in msg:
            msg = msg.replace('$XMS_BOLD$', '')
            self.ui.txt_log.setFontWeight(QFont.Bold)
            bold = True
        return bold, msg

    def _format_warnings_and_errors(self, msg, level):
        """Formats warnings green and errors blue or, if not using colors, wraps them in *****.

        Args:
            msg (str): The log message
            level (int): Log levelno

        Returns:
            (tuple): tuple containing:

                msg (str): Modified log message without the '$XMS_BOLD$'

                old_color (QColor): The original text color.

                use_colors (bool): Flag indicating if the color changed.
        """
        # Color warnings and errors or mark them with '*****'
        use_colors = self.display_text.get('use_colors', True)
        old_color = self.ui.txt_log.textColor()
        if level >= LogEchoQtHandler.log_level_error:
            LogEchoQSignalStream.logged_error = True
            if use_colors:
                self.ui.txt_log.setTextColor(QColor(255, 0, 0))  # Red
            else:
                msg = f'\n*****\n{msg}\n*****\n'
        elif level == LogEchoQtHandler.log_level_warning:
            if use_colors:
                self.ui.txt_log.setTextColor(QColor(255, 127, 39))  # Orange
            else:
                msg = f'\n*****\n{msg}\n*****\n'
        return msg, old_color, use_colors

    def processing_finished(self):
        """Called after mapping operation completes. Closes dialog if auto load option enabled."""
        self.logger.info(f'Elapsed time: {datetime.datetime.now() - self.start_time}\n')
        self._finished = True
        self.indicator.stop()
        self.ui.lbl_load_indicator.setVisible(False)
        self.ui.btn_box.button(QDialogButtonBox.Ok).setEnabled(True)  # Re-enable the 'Ok' button
        # errors_or_warnings = LogEchoQSignalStream.logged_error or LogEchoQSignalStream.logged_warning
        # ok_to_auto_close = self.testing or not errors_or_warnings
        ok_to_auto_close = False
        if ok_to_auto_close:  # No errors or warnings logged, check if auto close is enabled
            if self.ui.tog_auto_close.checkState() == Qt.Checked:
                # Close the dialog so we can send mapped data back to SMS
                self.done(QDialog.Accepted)
            else:
                self.ui.lbl_status.setText(self.display_text.get('success_prompt', 'Success'))
                self.ui.lbl_status.setStyleSheet('QLabel{color: rgb(0, 200, 0);}')
                self.ui.tog_auto_close.setEnabled(False)
        else:  # No auto close if warnings/errors and not testing
            if LogEchoQSignalStream.logged_error:
                self.ui.lbl_status.setText(self.display_text.get('error_prompt', 'Error'))
                self.ui.lbl_status.setStyleSheet('QLabel{color: rgb(255, 0, 0);}')
            elif LogEchoQSignalStream.logged_warning:
                self.ui.lbl_status.setText(self.display_text.get('warning_prompt', 'Warning'))
                self.ui.lbl_status.setStyleSheet('QLabel{color: rgb(255, 127, 39);}')
            else:
                self.ui.lbl_status.setText(self.display_text.get('success_prompt', 'Success'))
                self.ui.lbl_status.setStyleSheet('QLabel{color: rgb(0, 200, 0);}')
            self.ui.tog_auto_close.setCheckState(Qt.Unchecked)
            self.ui.tog_auto_close.setEnabled(False)


class FeedbackDialog(ProcessFeedbackDlg):
    """A dialog that displays feedback while running a worker thread."""
    def __init__(self, worker: FeedbackThread, parent: Optional[QWidget]):
        """
        Initialize the feedback dialog.

        Args:
            worker: The worker to run.
            parent: The parent window.
        """
        super().__init__(display_text=worker.display_text, logger_name=worker.logger_name, worker=worker, parent=parent)
        worker.setParent(self)
        self.testing = XmEnv.xms_environ_running_tests() == 'TRUE'


def run_feedback_dialog(worker: FeedbackThread, parent: Optional[QWidget] = None) -> QDialog.DialogCode:
    """
    Run a feedback dialog.

    Args:
        worker: Worker for the feedback dialog to run.
        parent: Parent window. Script runners should pass `None`, which indicates the parent should be parsed out of
            the command line arguments. Component event handlers always receive a parent and should pass it in.

    Returns:
        The dialog's result code.
    """
    ensure_qapplication_exists()

    if XmEnv.xms_environ_running_tests() != 'TRUE' and parent is None:
        parent_hwnd, main_hwnd, _ = xms_parent_dlg.parse_parent_window_command_args()
        qt_parent = xms_parent_dlg.get_parent_window_container(parent_hwnd)
        # Create the timer that keeps our Python dialog in the foreground of XMS.
        _ = windows_gui.create_and_connect_raise_timer(main_hwnd, qt_parent)  # Keep the timer in scope
    else:
        qt_parent = None
        main_hwnd = None

    feedback_dialog = FeedbackDialog(worker, parent)
    result = feedback_dialog.exec()
    if not result:
        XmEnv.report_export_aborted()

    if qt_parent is not None:
        windows_gui.raise_main_xms_window(main_hwnd)  # Bring top-level Python window to foreground

    return result


if __name__ == '__main__':
    logger_name = "xms.gui.dialogs"
    logger = logging.getLogger(logger_name)

    def _run_tool():
        import time
        logger.info("Starting feedback thread")
        time.sleep(1.0)
        logger.info("Finished feedback")

    app = QApplication([])
    testing = False
    tool_name = 'Sample Tool'
    display_text = {
        'title': 'Tool name',
        'working_prompt': f'Executing "{tool_name}" tool.',
        'error_prompt': 'Error(s) encountered while running tool.',
        'warning_prompt': 'Warning(s) encountered while running tool.',
        'success_prompt': 'Successfully ran tool.',
        'note': '',
        # 'auto_load': 'Close this dialog automatically when finished.',
        'log_format': '- %(message)s',
        'use_colors': True,
        'auto_load': 'testing' if testing else ''
    }
    win_cont = None
    ensure_qapplication_exists()
    worker = ProcessFeedbackThread(_run_tool, None)
    feedback_dlg = ProcessFeedbackDlg(display_text=display_text, logger_name=logger_name, worker=worker,
                                      parent=win_cont)
    feedback_dlg.setModal(False)
    feedback_dlg.testing = False
    dialog_result = feedback_dlg.exec()
    if feedback_dlg.testing:
        worker.processing_finished.emit()
