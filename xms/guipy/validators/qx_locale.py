"""
Module containing QxLocale, the locale that should be used by the Python UI.

Our Python code interacts with the user exclusively through Qt, which has localization features baked in from the
outset. Unfortunately, XMS has a lot of legacy code that never benefited from this convenience and does everything
manually, which means everything is in the "C" locale. Since fixing XMS is a lot of work (and adjusting our user
base to the new localization regime would be even more), we'll "fix" Python by telling Qt to use the "C" locale's
number formatting conventions.

Code that requires a locale for some reason should use this one so we're all consistent and can easily change it
later if necessary.
"""

# 1. Standard Python modules

# 2. Third party modules
from PySide6.QtCore import QLocale

# 3. Aquaveo modules

# 4. Local modules

__copyright__ = "(C) Copyright Aquaveo 2023"
__license__ = "All rights reserved"

#: The locale that should be used by the Python GUI.
QxLocale = QLocale(QLocale.English, QLocale.UnitedStates)
