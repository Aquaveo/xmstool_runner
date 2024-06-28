"""ProcessFeedbackThread class."""

__copyright__ = "(C) Copyright Aquaveo 2020"
__license__ = "All rights reserved"

# 1. Standard python modules

# 2. Third party modules
from PySide6.QtCore import QThread, Signal

# 3. Aquaveo modules

# 4. Local modules


class ProcessFeedbackThread(QThread):
    """
    Class used with ProcessFeedbackDialog.

    See `xms.guipy.dialogs.feedback_thread.FeedbackThread` and `xms.guipy.dialogs.process_feedback_dlg.FeedbackDialog`
    for a newer alternative that needs less boilerplate.
    """

    processing_finished = Signal()

    def __init__(self, do_work, parent):
        """Construct the worker.

        Args:
            do_work (method): method to execute
            parent (QWidget): parent widget
        """
        super().__init__(parent)
        self.do_work = do_work

    def run(self):
        """Do the work."""
        self.do_work()
        self.processing_finished.emit()
