"""Module for the `FeedbackThread` class and companion exceptions."""

__copyright__ = "(C) Copyright Aquaveo 2023"
__license__ = "All rights reserved"

# 1. Standard Python modules
import logging
from typing import Optional

# 2. Third party modules

# 3. Aquaveo modules
try:
    from xms.api.dmi import Query
except ImportError:
    Query = None
from xms.api.dmi import XmsEnvironment as XmEnv
from xms.guipy.dialogs.process_feedback_thread import ProcessFeedbackThread

# 4. Local modules


class ExpectedError(Exception):
    """
    An exception that is handled as an expected error when it escapes from `FeedbackThread._run()`.

    This exception can be raised to exit from `FeedbackThread._run()` and have an error message logged at the same time.
    It should be raised like `raise ExpectedError('Something bad happened')`. The `FeedbackThread` will then handle it
    by logging the message this was constructed with ('Something bad happened', in this case) as at the `error` level.
    No stack trace will be written, since this exception is meant for expected errors, like the user specifying
    nonsensical values.
    """
    pass


class ExitError(Exception):
    """
    An exception that is handled as an already-logged error when it escapes from `FeedbackThread._run()`.

    This exception can be raised to exit from `FeedbackThread._run()`. It should be raised like `raise ExitError()`. The
    `FeedbackThread` will then suppress it. Unlike `ExpectedError`, this exception does not result in an error message
    being written. Its main use case is for when a lower level of code logs an error and reports a failure, and a higher
    level just wants to bail out as quickly as possible without logging an error twice.
    """
    pass


class FeedbackThread(ProcessFeedbackThread):
    """
    A base class for background threads that run long tasks.

    To use this class, you'll want to derive something from it that sets `self.display_text` and overrides
    `self._run()`. Then you can pass instances to `xms.guipy.feedback.process_feedback_dlg.run_feedback_dialog()`.
    """
    def __init__(self, query: Optional[Query]):
        """
        Initialize the runner.

        Args:
            query: Interprocess communication object.
        """
        super().__init__(parent=None, do_work=self._run_wrapper)

        #: Messages and text to display in a feedback dialog while running the thread.
        self.display_text = {
            # Title of the dialog.
            'title': 'Running task...',
            # Display message for when the thread is running.
            'working_prompt': 'Running task, please wait...',
            # Display message for when a warning occurs.
            'warning_prompt': 'Warning(s) encountered during task. Review log output for details.',
            # Display message for when an error occurs.
            'error_prompt': 'Error(s) encountered during task. Review log output for details.',
            # Display message for when everything succeeds.
            'success_prompt': 'Task completed successfully.',
            # Text to display in a banner at the top. Banner is hidden if this is empty.
            'note': '',
            # Text to display next to the autoload checkbox. Box is hidden if this is empty.
            'auto_load': ''
        }

        module = self.__module__
        first_two_components = module.split('.')[:2]
        self.logger_name = '.'.join(first_two_components)

        if Query is None:
            self._query = None
        else:
            self._query: Query = query or Query()
        self._log: logging.Logger = logging.getLogger(self.logger_name)

    def _run_wrapper(self):
        """Wraps `self._run()` and handles generic stuff so derived classes can focus on their specific problems."""
        try:
            self._run()
        except ExpectedError as exc:
            self._log.error(str(exc))
        except ExitError:
            pass
        except Exception as exc:
            # All the feedback threads I've seen swallow any exceptions before they escape and just print a generic
            # error message. It's probably to avoid scaring the user, but it makes debugging a pain. We'll write a
            # stack trace to the debug log to ease debugging.
            self._log.error('An unexpected internal error occurred. Please contact Aquaveo tech support.')
            XmEnv.report_error(exc)

    def _run(self):
        """
        Run the thread.

        Derived classes should override this to do any necessary work.
        """
        # Note: Many existing feedback runners call this `_do_work()` and wrap the whole body in a `try...except...`
        # block that logs a generic error message. Derived classes should *not* imitate this. Only catch exceptions here
        # if you can do something useful with them, like try an alternative way to do the job or tell the user how to
        # fix it. The base class will take care of unexpected errors by telling the user something bad happened and
        # writing a stack trace.

        # This method will have access to `self._query` and `self._log`.

        # The exceptions defined above in this file are handled by this method's caller. Details in their docstrings.
        raise ExpectedError('Thread not implemented')
