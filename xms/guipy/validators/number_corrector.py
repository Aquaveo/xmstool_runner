"""Event filter for formatting numbers in edit fields for XMS Python dialogs."""

__copyright__ = "(C) Copyright Aquaveo 2019"
__license__ = "All rights reserved"

# 1. Standard python modules
import math
import re

# 2. Third party modules
from PySide6.QtCore import QEvent, QObject, Signal
from PySide6.QtGui import QDoubleValidator, QValidator

# 3. Aquaveo modules

# 4. Local modules
from xms.guipy.validators.qx_locale import QxLocale


class NumberCorrector(QObject):
    """Event filter for formatting numbers in edit fields for XMS Python dialogs."""
    MERICA_LOCALE = QxLocale
    DEFAULT_PRECISION = 10
    text_corrected = Signal()

    def __init__(self, parent=None):
        """Construct the event filter."""
        super().__init__(parent)

    def eventFilter(self, obj, event):  # noqa: N802
        """Validate text as it is being inputted.

        Args:
            obj (QObject): Qt object to handle event for
            event (QEvent): The Qt event to handle

        Returns:
            (bool): True if the event was handled
        """
        try:
            event_type = event.type()
            if event_type in [QEvent.FocusOut, QEvent.Close] and obj:
                valid = obj.validator()
                is_dbl = isinstance(valid, QDoubleValidator)
                curr_text = obj.text()
                if not curr_text:
                    curr_text = '0.0' if is_dbl else '0'
                    obj.setText(curr_text)
                    obj.setModified(True)
                state, val, ok = obj.validator().validate(obj.text(), 0)
                if is_dbl and (state == QValidator.Intermediate or state == QValidator.Invalid):
                    # Change the text to be something valid
                    prec = valid.decimals()
                    current, ok = NumberCorrector.MERICA_LOCALE.toDouble(obj.text())
                    if ok:  # Is a valid double, but out of range
                        if current < valid.bottom():
                            obj.setText(f'{valid.bottom():.{prec}f}')
                        else:
                            obj.setText(f'{valid.top():.{prec}f}')
                    else:
                        obj.undo()
                        # obj.setText(f'{valid.bottom():.{prec}f}')
                    obj.setModified(True)
                if is_dbl:
                    # add/trim trailing zeros as needed
                    current, ok = NumberCorrector.MERICA_LOCALE.toDouble(obj.text())
                    s = self.format_double(current)
                    obj.setText(s)
                    obj.setModified(True)
                    self.text_corrected.emit()
                if not is_dbl and (state == QValidator.Intermediate or state == QValidator.Invalid):  # Integers
                    current, ok = NumberCorrector.MERICA_LOCALE.toInt(obj.text())
                    if ok:  # Is a valid double, but out of range
                        if current <= valid.bottom():
                            obj.setText(NumberCorrector.MERICA_LOCALE.toString(valid.bottom()))
                        else:
                            obj.setText(NumberCorrector.MERICA_LOCALE.toString(valid.top()))
                    else:
                        obj.setText(NumberCorrector.MERICA_LOCALE.toString(valid.bottom()))
                    obj.setModified(True)
        except AttributeError:
            # this can get called on a QWidget that doesn't have the validator(), text() and other methods
            # for these objects just pass the event on
            pass
        return super().eventFilter(obj, event)

    @staticmethod
    def format_double(value, prec=DEFAULT_PRECISION, version=2):
        """Returns a double as a formatted string.

        Args:
            value (float): Number to format
            prec (int): Maximum number of significant figures to include in the string
                (switch to scientific notation if needed)
            version (int): Version to use (1, or 2 are the options right now. See test_format_double())

        Returns:
            (str): See description
        """
        if version == 1:
            # This makes numbers like 1e25 appear like '10000000000000000905969664.0'
            display_text = f'{value:.{prec}f}'
            display_text = re.sub('0+$', '', display_text)
            if display_text.endswith('.'):
                display_text += '0'

        elif version == 2:
            # Like using 'g' but switches between e and f better and better formatting
            # Idea from https://stackoverflow.com/questions/4626338
            if abs(value) == 0.0:
                display_text = '0.0'
            else:
                log_value = math.log10(abs(value))
                if log_value < -prec or log_value > prec:
                    display_text = f'{value:.{prec}e}'
                    display_text = re.sub('0(0*)e', '0e', display_text)  # '1.000000000e+41 -> 1.0e+41
                else:
                    display_text = f'{value:.{prec}f}'.rstrip('0')
                    if display_text.endswith('.'):
                        display_text += '0'

        # This is what we were doing in C++, but it does not work with PySide6. Since this method takes a float,
        # we should not have to worry about locale.
        # display_text = MERICA_LOCALE.toString(value, 'f', prec)
        # dec_pt = MERICA_LOCALE.decimalPoint()
        # if dec_pt not in display_text:  # Make sure there is always one digit of precision.
        #     display_text += dec_pt
        #     display_text += '0'
        # else:  # Trim superfluous trailing zeros.
        #     display_text = re.sub('0+$', '', display_text)
        #     if display_text.endswith(dec_pt):
        #         display_text += '0'
        # display_text.replace(MERICA_LOCALE.groupSeparator(), '')
        return display_text
