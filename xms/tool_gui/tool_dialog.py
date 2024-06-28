"""ToolDialog class."""

# 1. Standard python modules
import datetime
import os
import traceback
from typing import List, Optional
import webbrowser

# 2. Third party modules
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWebEngineCore import QWebEnginePage
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import (QDialog, QDialogButtonBox, QHBoxLayout, QScrollArea, QSplitter, QToolBar, QVBoxLayout,
                               QWidget)

# 3. Aquaveo modules
from xms.guipy.dialogs.message_box import message_with_ok
from xms.guipy.dialogs.process_feedback_dlg import ProcessFeedbackDlg
from xms.guipy.dialogs.process_feedback_thread import ProcessFeedbackThread
from xms.guipy.dialogs.xms_parent_dlg import ensure_qapplication_exists, get_xms_icon, XmsDlg
from xms.guipy.resources.help_finder import HelpFinder
from xms.guipy.widgets.widget_builder import setup_toolbar
from xms.tool_core import Argument, Tool, ToolError, ToolInterface  # noqa I100,I201
from xms.tool_gui.param_qt_helper import ParamQtHelper

# 4. Local modules

__copyright__ = "(C) Copyright Aquaveo 2020"
__license__ = "All rights reserved"


class ToolDialog(XmsDlg):
    """Dialog for entering values for tool arguments."""
    back_icon = ':/resources/icons/back.svg'
    forward_icon = ':/resources/icons/forward.svg'

    def __init__(self, win_cont: Optional[QWidget], tool: Tool, tool_arguments: List[Argument], title: str = '',
                 description: str = '', tool_url: Optional[str] = None, tool_uuid: str = ''):
        """Initializes the class, sets up the UI.

        Args:
            win_cont (Optional[QWidget]): Parent window.
            tool (Tool): The tool to run
            tool_arguments (List[Argument]): Tool argument list.
            title (str): Dialog title.
            description (str): Description to appear on the side of the dialog.
            tool_url (str): Optional override for the tool help URL.
            tool_uuid (str): The UUID of the tool to use for documentation.
        """
        super().__init__(win_cont, 'xmstool_gui.XmsTool_Dailog')
        self.testing = win_cont is None
        self.tool_arguments = tool_arguments
        self.tool_interface = ToolInterface(tool_arguments)
        self.interface_values = []
        self.web_page = None
        self.web_page_loaded = False
        self.web_load_error = False
        self.setting_error_text = False
        self.tool_url = tool_url
        self.btn_actions = {}  # Web view navigation buttons
        self.title = title
        self.description = description
        self.tool = tool
        self.tool_uuid = tool_uuid

        # Add the simplified XMS tool arguments to a dictionary, and use that to create a
        # param.Parameterized class, which will be used for the layout
        self._set_up_param_helper(tool_arguments)
        self.widgets = dict()

        if len(title) > 0:
            self.setWindowTitle(title)
        else:
            self.setWindowTitle('Tool')
        self.set_up_ui()
        self.adjustSize()
        self.resize(self.size().width() * 1.5, self.size().height())
        self._on_argument_changed(force_change=True)

    def _set_up_param_helper(self, tool_arguments):
        """Initialize the param helper.

        Args:
            tool_arguments (list): Maybe, unused
        """
        self.param_helper = ParamQtHelper(self)
        self.param_helper.end_do_param_widgets.connect(self._on_argument_changed)

    def accept(self):
        """Accept."""
        # First check for param
        message = self.tool.validate(self.tool_arguments)
        if message:
            title = self.tool.name
            message_with_ok(self, message, title, win_icon=self.windowIcon())
        else:
            super().accept()

    def set_up_ui(self):
        """Set up the dialog widgets."""
        # Dialog QVBoxLayout with QTabWidget then QDialogButtonBox
        self._set_layout('', 'top_layout', QVBoxLayout())
        self.widgets['h_layout'] = QHBoxLayout()

        self._set_up_ui_arguments()

        # Set up the description pane
        self._add_web_view()
        self.add_splitter()

        self.widgets['h_layout'].addWidget(self.widgets['splitter'])
        self.widgets['top_layout'].addLayout(self.widgets['h_layout'])
        self.widgets['btn_box'] = QDialogButtonBox()

        self.widgets['top_layout'].addWidget(self.widgets['btn_box'])

        # set all widget values and hide/show
        self.param_helper.do_param_widgets(None)

        # QDialogButtonBox with Ok and Cancel buttons
        self.widgets['btn_box'].setOrientation(Qt.Horizontal)
        self.widgets['btn_box'].setStandardButtons(
            QDialogButtonBox.Cancel | QDialogButtonBox.Ok | QDialogButtonBox.Help)
        self.widgets['btn_box'].accepted.connect(self.accept)
        self.widgets['btn_box'].rejected.connect(super().reject)
        self.widgets['btn_box'].helpRequested.connect(self.help_requested)

    def _default_html(self):
        """Returns the default html string for the description window."""
        return """
              <!DOCTYPE html>
              <html>
              <body>

              <h1 style="color:blue;">{0}</h1>
              <p style="color:black;">{1}</p>

              </body>
              </html>
              """

    def _error_html(self):
        """Returns the error html string for the description window."""
        error_html = """
                     <!DOCTYPE html>
                     <html>
                     <head>
                     <title>Use Help Button</title>
                     </head>
                     <body>
                     <h1 style="color:blue;">{0}</h1>
                     <p style="color:red;">Loading web content failed: {1}</p>
                     <p style="color:black;">{2}</p>
                     <p style="color:black;">Use the Help button to load help page in a web browser.{1}</p>
                     </body>
                     </html>
                     """
        return error_html

    def _on_web_page_loaded(self, loaded):
        """Set the description to the tool web page once it loads.

        Args:
            loaded (bool): True if the web page loaded successfully
        """
        if self.setting_error_text:  # pragma no cover - not sure if this is necessary
            return  # Tests don't hit this but it may need to be here. See comment below.

        if loaded:
            self.widgets['web_browser'].setPage(self.web_page)
            self.widgets['navigation_bar'].show()
        else:
            self.setting_error_text = True  # Don't display the error text HTML as the URL
            # Make sure we get the original URL if initial web page load fails.
            url = self.widgets['web_browser'].url().toDisplayString() if self.tool_url is None else self.tool_url
            str_html = self._error_html().format(self.title, url, self.description)
            self.widgets['web_browser'].setHtml(str_html)
            self.setting_error_text = False
            self.web_load_error = True
        self.web_page_loaded = True

    def _on_url_changed(self, loaded):  # pragma no cover - not testing web navigation
        """Enable/disable navigation buttons when user changes the web view page."""
        # I added the try/except because for some reason this gets called when the dialog is closing and it throws
        # "Internal C++ object (PySide2.QtWidgets.QAction) already deleted."
        try:
            can_go_back = self.widgets['web_browser'].history().canGoBack()
            can_go_forward = self.widgets['web_browser'].history().canGoForward()
            self.widgets['navigation_bar'].widgetForAction(self.btn_actions[self.back_icon]).setEnabled(can_go_back)
            self.widgets['navigation_bar'].widgetForAction(
                self.btn_actions[self.forward_icon]).setEnabled(can_go_forward)
        except Exception:
            pass

    def _on_argument_changed(self, force_change=False):
        """Handles changing an argument, by calling the tool's enable_arguments.

        Args:
            force_change (bool): flag to force that the parameters have changed
        """
        changed = self.tool_interface.apply_interface_values(self.interface_values)
        if changed or force_change:
            self.tool.enable_arguments(self.tool_arguments)
            self.interface_values = self.tool_interface.get_interface_values()
            clear_layout(self.widgets['arg_layout'])
            self._set_up_param_helper(self.tool_arguments)
            self.param_helper.add_params_to_layout(self.widgets['arg_layout'], self.interface_values)
            self.widgets['arg_layout'].addStretch()
            self.param_helper.do_param_widgets(None)  # Get values from arguments into params

    def _add_web_view(self):
        """Add the description web view pane."""
        # Create a widget to layout the navigation bar and web view.
        self.widgets['description_widget'] = QWidget()
        self._set_layout('description_widget', 'description_layout', QVBoxLayout())
        # Create the web view. Initially has the static text defined in the tool class.
        self.widgets['web_browser'] = QWebEngineView()
        self.widgets['web_browser'].urlChanged.connect(self._on_url_changed)
        self.web_page = QWebEnginePage()  # Load the URL in the background
        self.web_page.loadFinished.connect(self._on_web_page_loaded)
        # Back and forward navigation buttons
        self._add_navigation_bar()
        self.widgets['description_layout'].addWidget(self.widgets['navigation_bar'])
        self.widgets['description_layout'].addWidget(self.widgets['web_browser'])
        # Initialize the text in the description web view.
        self._set_up_ui_browser_initial_text()

    def add_splitter(self):
        """Adds a QSplitter between the tables so the sizes can be adjusted."""
        # The only way this seems to work right is to parent it to
        # self and then insert it into the layout.
        self.widgets['splitter'] = QSplitter(self)
        self.widgets['splitter'].setOrientation(Qt.Horizontal)
        self.widgets['splitter'].addWidget(self.widgets['scrollable_area'])
        self.widgets['splitter'].addWidget(self.widgets['description_widget'])
        self.widgets['splitter'].setSizes([50, 50])
        self.widgets['splitter'].setStyleSheet(
            'QSplitter::handle:horizontal { background-color: lightgrey; }'
            'QSplitter::handle:vertical { background-color: lightgrey; }'
        )
        self.widgets['splitter'].setAccessibleName('Splitter')
        self.widgets['splitter'].setCollapsible(0, False)
        self.widgets['splitter'].setCollapsible(1, True)

    def _add_navigation_bar(self):
        """Add the navigation bar for the description web view."""
        self.widgets['navigation_bar'] = QToolBar()
        button_list = [
            [self.back_icon, 'Go Back', self.widgets['web_browser'].back],
            [self.forward_icon, 'Go Forward', self.widgets['web_browser'].forward],
        ]
        self.btn_actions = setup_toolbar(self.widgets['navigation_bar'], button_list)
        self.widgets['navigation_bar'].hide()  # Don't show until the web page is loaded

    def _set_up_ui_browser_initial_text(self):
        """Set the initial test for the description pane."""
        self.update_tool_help_url()
        title = f'{self.title} (loading web content...)' if self.tool_url else self.title
        str_html = self._default_html().format(title, self.description)
        self.widgets['web_browser'].setHtml(str_html)
        if self.tool_url:  # Start loading the web page if there is one.
            self.web_page.load(self.tool_url)

    def update_tool_help_url(self):
        """Update the tool help URL used for web page and help button."""
        if self.tool_url is None:
            self.tool_url = HelpFinder.help_url(
                dialog_help_url='https://www.xmswiki.com/wiki/Tool_Dialog_Help',
                identifier=self.tool_uuid,
                default='',
                category='xmstool'
            )

    def _set_up_ui_arguments(self):
        """Set up the general widgets."""
        self.widgets['args_widget'] = QWidget()
        self._set_layout('args_widget', 'arg_layout', QVBoxLayout())
        self.widgets['arg_layout'].addStretch()
        self.widgets['scrollable_area'] = QScrollArea(self)
        self.widgets['scrollable_area'].setWidget(self.widgets['args_widget'])
        self.widgets['scrollable_area'].setWidgetResizable(True)

    def _set_layout(self, parent_name, layout_name, layout):
        """Adds a layout to the parent.

        Args:
            parent_name (str): Name of parent widget in self.widgets or '' for self
            layout_name (QLay): Name of layout in parent widget
            layout (str): QtLayout to be used
        """
        self.widgets[layout_name] = layout
        if parent_name:
            parent = self.widgets[parent_name]
        else:
            parent = self
        parent.setLayout(self.widgets[layout_name])

    def help_requested(self):
        """Called when the Help button is clicked."""
        if self.tool_url:
            webbrowser.open(self.tool_url)
        else:
            webbrowser.open('https://www.xmswiki.com')

    def get_param_widget(self, name: str) -> Optional[QWidget]:
        """Get widget for argument by name (used for testing).

        Args:
            name (str): The widget name.

        Returns:
            (Optional[QWidget]): The Qt widget.
        """
        param = self.param_helper.param_dict.get(name, None)
        if param is not None:
            return param.get('value_widget', None)
        return None

    def get_param_widget_names(self) -> List[str]:
        """Get names of params from the param helper (used for testing).

        Returns:
            (List[str]): The names of the param widgets.
        """
        return list(self.param_helper.param_dict.keys())


def clear_layout(layout, delete_widgets=True):
    """Clear all widgets under a layout.

    Args:
        layout: The QLayout.
        delete_widgets: Should the widgets be deleted.
    """
    item = layout.takeAt(0)
    while item is not None:
        if delete_widgets:
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        child_layout = item.layout()
        if child_layout is not None:
            clear_layout(child_layout, delete_widgets)
        item = layout.takeAt(0)


def _override_default_arguments(tool, json_object):
    """Override a tool's default argument values with those specified in JSON.

    Notes:
        The `description` key/value pair must always be specified and must match the text in the class definition.
        Any other key/value pairs will override the default value for that argument.

    Args:
        tool (Tool): The tool
        json_object (dict): The parsed JSON argument specifier dict

    Returns:
        (list): List of arguments used from previous tool run.
    """
    initial_arguments = [argument.to_dict() for argument in tool.initial_arguments()]
    for initial_argument in initial_arguments:
        arg_name = initial_argument.get('name', '')
        for specified_argument in json_object['arguments']:
            if specified_argument.get('name', '') == arg_name:
                initial_argument.update(specified_argument)
                break
    return tool.get_arguments_from_results({'arguments': initial_arguments})


def _run_results_dialog(module_name, class_name, parent):
    """Run a custom, tool-defined results dialog after the tool finishes running.

    Args:
        module_name (str): Import path to the dialog module
        class_name (str): Class namem of the QDialog
        parent (QDialog): The parent dialog
    """
    module = __import__(module_name, fromlist=[class_name])
    klass = getattr(module, class_name)
    dlg = klass(parent)
    return dlg.exec()


def run_tool_dialog(input_json, win_cont, tool) -> Optional[dict]:
    """Run the tool dialog for a tool.

    Args:
        input_json (dict): Input JSON.
        win_cont (:obj:'PySide6.QtWidgets.QWidget'): The window container.
        tool (xms.tool.Tool): The tool.

    Returns:
        bool: True if dialog was accepted, False if user canceled
    """
    # check for saved arguments and load them
    tool_arguments = None
    using_default_override = input_json.get('using_default_override', False)
    if using_default_override:
        tool_arguments = _override_default_arguments(tool, input_json)
    elif 'arguments' in input_json:
        tool_arguments = tool.get_arguments_from_results(input_json)
    tool_name = input_json.get('tool_name', tool.__class__.__name__)
    tool_description = input_json.get('tool_description', '')
    tool_uuid = input_json.get('tool_uuid', '')

    if tool_arguments is None:
        tool_arguments = tool.initial_arguments()
    else:
        if not tool.validate_from_history(tool_arguments):
            icon_path = get_xms_icon()
            icon = None
            if icon_path:
                icon = QIcon(icon_path)
            message = ('The arguments in the history do not match the current tool arguments. '
                       'The default tool arguments will be used.')
            message_with_ok(win_cont, message, 'Argument Mismatch', win_icon=icon)
            tool_arguments = tool.initial_arguments()
    tool_dialog = ToolDialog(win_cont,
                             tool,
                             tool_arguments,
                             title=tool_name,
                             description=tool_description,
                             tool_uuid=tool_uuid)
    results = None
    if tool_dialog.exec() == QDialog.Accepted:
        print('Running tool \'{0}\' at {1}'.format(tool.name, datetime.datetime.now()))
        run_tool_with_feedback(win_cont, tool, tool_arguments)
        # tool.send_output_to_xms()
        results = tool.results
    return results


def run_tool_with_feedback(win_cont, tool, tool_arguments, auto_str='', modal=False):
    """Run a tool using the feedback dialog.

    Args:
        win_cont (:obj:'PySide6.QtWidgets.QWidget'): The window container.
        tool (xms.tool.Tool): The tool.
        tool_arguments (list): The tool arguments.
        auto_str (str): Auto load string
        modal (bool): Flag to run the dialog as modal instead of modeless

    Returns:
        bool: True if dialog was accepted, False if user canceled
    """
    def _run_tool():
        try:
            tool.run_tool(tool_arguments, validate_arguments=False)
        except ToolError:
            # a ToolError should have already been reported
            pass
        except Exception:
            call_stack = traceback.format_exc()
            tool.logger.error(f'Unexpected problem running tool "{tool.name}".  More information:\n{call_stack}')

    tool.echo_output = False
    testing = win_cont is None
    display_text = {
        'title': tool.name,
        'working_prompt': f'Executing "{tool.name}" tool.',
        'error_prompt': 'Error(s) encountered while running tool.',
        'warning_prompt': 'Warning(s) encountered while running tool.',
        'success_prompt': 'Successfully ran tool.',
        'note': '',
        # 'auto_load': 'Close this dialog automatically when finished.',
        'log_format': '- %(message)s',
        'use_colors': True,
        'auto_load': 'testing' if testing else auto_str
    }
    ensure_qapplication_exists()
    worker = ProcessFeedbackThread(_run_tool, None)
    feedback_dlg = ProcessFeedbackDlg(
        display_text=display_text, logger_name=tool.__class__.__module__, worker=worker, parent=win_cont
    )
    if modal:
        feedback_dlg.setModal(True)
    if tool.results_dialog_module:
        worker.processing_finished.connect(
            lambda: _run_results_dialog(tool.results_dialog_module, tool.results_dialog_class, feedback_dlg)
        )
    feedback_dlg.testing = feedback_testing_mode()
    dialog_result = feedback_dlg.exec()
    if feedback_dlg.testing:
        worker.processing_finished.emit()
    return dialog_result


def get_test_files_path():
    """Returns the full path to the 'tests/files' directory.

    Returns:
        (str): See description.
    """
    file_dir = os.path.dirname(os.path.realpath(__file__))
    files_path = os.path.join(file_dir, '..', '..', 'tests', 'files')
    return os.path.abspath(files_path)


def feedback_testing_mode() -> bool:
    """Should feedback dialog be in testing mode."""
    return 'XMSTOOL_GUI_TESTING' in os.environ
