"""Helper class for rendering tool arguments in Qt dialogs."""

__copyright__ = "(C) Copyright Aquaveo 2019"
__license__ = "All rights reserved"

# 1. Standard python modules
import os

# 2. Third party modules
import pandas as pd
from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QDoubleValidator, QIntValidator
from PySide6.QtWidgets import (QCheckBox, QComboBox, QFileDialog, QHBoxLayout, QLabel, QLineEdit, QPushButton,
                               QSizePolicy)

# 3. Aquaveo modules
from xms.guipy import settings
from xms.guipy.validators.number_corrector import NumberCorrector
from xms.guipy.widgets.table_with_tool_bar import TableWithToolBar
from xms.tool_core.table_definition import TableDefinition

# 4. Local modules


class ParamQtHelper(QObject):
    """Add widgets to layout for a parameterized object."""

    end_do_param_widgets = Signal()
    NO_FILE_SELECTED = '(none selected)'

    def __init__(self, parent_dialog):
        """Initializes the class, sets up the ui.

        Args:
            parent_dialog (QObject): The parent dialog.
        """
        super().__init__()
        self.parent_dialog = parent_dialog
        self.param_dict = dict()
        self.do_param_widgets_call_count = 0
        self.param_horizontal_layouts = dict()
        self.param_groups = dict()

    def add_params_to_layout(self, layout, params: list[dict[str, object]]):
        """Add param objects to the layout.

        Args:
            layout (QBoxLayout): The layout to append to
            params (QObject): Qt parent of the param
        """
        # get param classes ordered by original precedence and add them to the vertical layout
        for param in params:
            self.add_param(layout, param)

    def add_param(self, layout, param: dict):  # noqa: C901
        """Add param objects.

        Args:
            layout: The layout to append to
            param: The param object
        """
        ptype = param['type']
        # widgets = widget_depends[param_name] if widget_depends and param_name in widget_depends else []
        widgets = []
        param_name = param['name']
        label_str = param['description']
        file_filter = param.get('file_filter', None)
        default_suffix = param.get('default_suffix', None)
        select_folder = False
        if len(label_str) > 0 and ptype != 'Boolean':
            widget_label = label_str + ':'
            widgets.append(QLabel(widget_label))
            widgets[-1].setAccessibleName(param_name + ' label')
            layout.addWidget(widgets[-1])

        value_action = None
        if ptype == 'StringSelector':
            widgets.append(QComboBox())
            layout.addWidget(widgets[-1])
            widgets[-1].addItems(param['choices'])
            widgets[-1].currentIndexChanged.connect(lambda: self.do_param_widgets(param_name))
            widgets[-1].currentIndexChanged.connect(lambda: self.on_end_do_param_widgets())
            widgets[-1].setAccessibleName(param_name)
            value_widget = widgets[-1]
            value_setter = widgets[-1].setCurrentText
            value_getter = widgets[-1].currentText
            is_file_argument = False
        elif ptype == 'Number':
            widgets.append(QLineEdit())
            layout.addWidget(widgets[-1])
            validator = QDoubleValidator(self)
            widgets[-1].setValidator(validator)
            widgets[-1].installEventFilter(NumberCorrector(self))
            widgets[-1].editingFinished.connect(lambda: self.do_param_widgets(param_name))
            widgets[-1].editingFinished.connect(lambda: self.on_end_do_param_widgets())
            widgets[-1].setAccessibleName(param_name)
            value_widget = widgets[-1]
            value_setter = widgets[-1].setText
            value_getter = lambda: float(widgets[-1].text())  # noqa: E731
            is_file_argument = False
        elif ptype == 'Integer':
            widgets.append(QLineEdit())
            layout.addWidget(widgets[-1])
            widgets[-1].setValidator(QIntValidator())
            widgets[-1].editingFinished.connect(lambda: self.do_param_widgets(param_name))
            widgets[-1].editingFinished.connect(lambda: self.on_end_do_param_widgets())
            widgets[-1].setAccessibleName(param_name)
            value_widget = widgets[-1]
            value_setter = widgets[-1].setText
            value_getter = lambda: int(widgets[-1].text())  # noqa: E731
            is_file_argument = False
        elif ptype == 'SelectFile':
            hor_layout = QHBoxLayout()
            layout.addLayout(hor_layout)
            widgets.append(QPushButton('Select File...'))
            button = widgets[-1]
            hor_layout.addWidget(button)
            button.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
            widgets[-1].setAccessibleName(param_name + '_select')
            # connect to the button click
            widgets.append(QLabel())
            hor_layout.addWidget(widgets[-1])
            button.clicked.connect(lambda: self.do_open_selector(param_name, widgets[-1]))
            widgets[-1].setAccessibleName(param_name)
            value_widget = widgets[-1]
            value_setter = widgets[-1].setText
            value_getter = widgets[-1].text
            value_action = button
            is_file_argument = True
        elif ptype == 'SaveFile':
            hor_layout = QHBoxLayout()
            layout.addLayout(hor_layout)
            widgets.append(QPushButton('Save As...'))
            button = widgets[-1]
            hor_layout.addWidget(button)
            button.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
            widgets[-1].setAccessibleName(param_name + '_select')
            # connect to the button click
            widgets.append(QLabel())
            hor_layout.addWidget(widgets[-1])
            button.clicked.connect(lambda: self.do_save_as_selector(param_name, widgets[-1]))
            widgets[-1].setAccessibleName(param_name)
            value_widget = widgets[-1]
            value_setter = widgets[-1].setText
            value_getter = widgets[-1].text
            value_action = button
            is_file_argument = True
        elif ptype == 'SelectFolder':
            hor_layout = QHBoxLayout()
            layout.addLayout(hor_layout)
            widgets.append(QPushButton('Select File...'))
            button = widgets[-1]
            hor_layout.addWidget(button)
            button.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
            widgets[-1].setAccessibleName(param_name + '_select')
            # connect to the button click
            widgets.append(QLabel())
            hor_layout.addWidget(widgets[-1])
            button.clicked.connect(lambda: self.do_open_selector(param_name, widgets[-1]))
            widgets[-1].setAccessibleName(param_name)
            value_widget = widgets[-1]
            value_setter = widgets[-1].setText
            value_getter = widgets[-1].text
            value_action = button
            is_file_argument = True
            select_folder = True
        elif ptype == 'SaveFolder':
            hor_layout = QHBoxLayout()
            layout.addLayout(hor_layout)
            widgets.append(QPushButton('Save As...'))
            button = widgets[-1]
            hor_layout.addWidget(button)
            button.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
            widgets[-1].setAccessibleName(param_name + '_select')
            # connect to the button click
            widgets.append(QLabel())
            hor_layout.addWidget(widgets[-1])
            button.clicked.connect(lambda: self.do_save_as_selector(param_name, widgets[-1]))
            widgets[-1].setAccessibleName(param_name)
            value_widget = widgets[-1]
            value_setter = widgets[-1].setText
            value_getter = widgets[-1].text
            value_action = button
            is_file_argument = True
            select_folder = True
        elif ptype == 'String':
            widgets.append(QLineEdit())
            layout.addWidget(widgets[-1])
            widgets[-1].editingFinished.connect(lambda: self.do_param_widgets(param_name))
            widgets[-1].editingFinished.connect(lambda: self.on_end_do_param_widgets())
            widgets[-1].setAccessibleName(param_name)
            value_widget = widgets[-1]
            value_setter = widgets[-1].setText
            value_getter = widgets[-1].text
            is_file_argument = False
        elif ptype == 'Boolean':
            widgets.append(QCheckBox(label_str))
            layout.addWidget(widgets[-1])
            widgets[-1].clicked.connect(lambda: self.do_param_widgets(param_name))
            widgets[-1].clicked.connect(lambda: self.on_end_do_param_widgets())
            widgets[-1].setAccessibleName(param_name)
            value_widget = widgets[-1]
            value_setter = widgets[-1].setChecked
            value_getter = widgets[-1].isChecked
            is_file_argument = False
        elif ptype == 'Table':
            widgets.append(TableWithToolBar())
            table_definition = param['table_definition']
            if not isinstance(table_definition, TableDefinition):
                table_def = TableDefinition.from_dict(table_definition)
            else:
                table_def = table_definition
            widgets[-1].setup(table_def, param['value'])
            layout.addWidget(widgets[-1])
            widgets[-1].data_changed.connect(lambda: self.do_param_widgets(param_name))
            widgets[-1].data_changed.connect(lambda: self.on_end_do_param_widgets())
            widgets[-1].setAccessibleName(param_name)
            value_widget = widgets[-1]
            value_setter = widgets[-1].set_values
            value_getter = widgets[-1].get_values
            is_file_argument = False
        else:
            raise RuntimeError(f'Unsupported "param" parameter type: {ptype}')

        self.param_dict[param_name] = {
            'parent_class': param,
            'value_widget': value_widget,
            'value_getter': value_getter,
            'value_setter': value_setter,
            'widget_list': widgets,
            'is_file_argument': is_file_argument,
            'file_filter': file_filter,
            'default_suffix': default_suffix,
            'select_folder': select_folder,
        }
        if value_action is not None:
            self.param_dict[param_name]['value_action'] = value_action

    def do_save_as_selector(self, param_name, file_edit_field):
        """Display a file save as dialog.

        Args:
            param_name: Name of the parameter
            file_edit_field (QLineEdit): Qt widget holding descriptive text
        """
        p_dict = self.param_dict[param_name]
        curr_filename = p_dict['value_getter']()
        path = ''
        if curr_filename:
            path = os.path.dirname(curr_filename)
        if not os.path.exists(path):
            path = settings.get_file_browser_directory()
        file_filter = p_dict['file_filter']
        window_text = 'Save Folder' if p_dict['select_folder'] else 'Save File'
        dlg = QFileDialog(self.parent_dialog, window_text, path, file_filter)
        dlg.setLabelText(QFileDialog.Accept, "Save")
        dlg.setFileMode(QFileDialog.AnyFile)
        dlg.setDefaultSuffix(p_dict['default_suffix'])
        if p_dict['select_folder']:
            dlg.setOption(QFileDialog.ShowDirsOnly, on=True)
            dlg.setFileMode(QFileDialog.Directory)
        if dlg.exec():
            p_dict['value'] = dlg.selectedFiles()[0]
            file_edit_field.setText(dlg.selectedFiles()[0])
        self.do_param_widgets(param_name)
        self.on_end_do_param_widgets()

    def do_open_selector(self, param_name, file_edit_field):
        """Display a file open selector dialog.

        Args:
            param_name: Name of the parameter
            file_edit_field (QLineEdit): Qt widget holding descriptive text
        """
        p_dict = self.param_dict[param_name]
        curr_filename = p_dict['value_getter']()
        path = ''
        if curr_filename:
            path = os.path.dirname(curr_filename)
        if not os.path.exists(path):
            path = settings.get_file_browser_directory()
        file_filter = p_dict['file_filter']
        window_text = 'Select Folder' if p_dict['select_folder'] else 'Select File'
        dlg = QFileDialog(self.parent_dialog, window_text, path, file_filter)
        dlg.setLabelText(QFileDialog.Accept, "Select")
        if p_dict['select_folder']:
            dlg.setOption(QFileDialog.ShowDirsOnly, on=True)
            dlg.setFileMode(QFileDialog.Directory)
        if dlg.exec():
            p_dict['parent_class']['value'] = dlg.selectedFiles()[0]
            file_edit_field.setText(dlg.selectedFiles()[0])
        self.do_param_widgets(param_name)
        self.on_end_do_param_widgets()

    def on_end_do_param_widgets(self):
        """Sends a signal after do_param_widgets is called."""
        self.end_do_param_widgets.emit()

    def do_param_widgets(self, param_name):
        """Get param values from widgets and update widgets.

        Args:
            param_name: Name of the parameter
        """
        if self.do_param_widgets_call_count > 0:
            return
        self.do_param_widgets_call_count += 1

        if param_name is not None:
            p_dict = self.param_dict[param_name]
            # get the value for this parameter for its widget and set it in the param class
            val = p_dict['value_getter']()
            if not isinstance(val, pd.DataFrame) and val == self.NO_FILE_SELECTED and p_dict['is_file_argument']:
                val = ''
            p_dict['parent_class']['value'] = val

        # setting a param value can trigger changes to other members of the class so we need
        # to set the values of the other params to the widgets
        for name in self.param_dict.keys():
            if name == param_name:
                continue
            self._set_param_widget_value(name)

        self.do_param_widgets_call_count -= 1

    def _set_param_widget_value(self, param_name):
        """Sets widgets for a param object.

        Args:
            param_name: Name of the parameter
        """
        p_dict = self.param_dict[param_name]
        val = p_dict['parent_class']['value']
        if p_dict['parent_class']['type'] in ['Number', 'Integer']:
            val = str(val)
        if p_dict['is_file_argument'] and not val:
            p_dict['value_setter'](self.NO_FILE_SELECTED)
        elif p_dict['value_setter'] is not None:
            p_dict['value_setter'](val)
