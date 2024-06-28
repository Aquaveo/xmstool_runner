"""Manage list of toolbox tools."""
from datetime import datetime
from importlib import metadata
import os
from typing import Any, Optional
import uuid
import xml.etree.ElementTree as Et

from xms.tool_gui.tool_dialog import run_tool_dialog


def find_xms_model_definitions():
    """Package finder for XMS DMI components and model interfaces.

    This script is called by XMS on startup. It will be called with the Python installed with XMS. To register a package
    for loading on XMS startup, install to the XMS Python as follows:
        1. Define an 'xms.dmi.interfaces' entry point. The text of the key is irrelevant, but should be unique among all
        registered packages. The value should be the package name.

        2. Define an 'XMS DMI Definition' classifier containing the import path to the component/model interface
        definition file. Only one definition per package is supported. Must specify the format of the definition file
        ('DIN' or 'XML'). Can optionally define 'XMS DMI Migration' classifiers using the same format to load migration
        definitions.
    Example setuptools.setup call in setup.py:
    ::
        setup(
            name='xmsexample',
            version='0.0.0',
            packages=find_packages(),
            include_package_data=True,

            # Register an entry point so XMS can find the package on startup.
            entry_points={
                'xms.dmi.interfaces': 'UNIQUE_KEY = xmsexample'
            },

            # Define a classifier pointing to the definition file. Must be relative from package import root.
            classifiers=[
                'XMS DMI Definition :: XML :: xmsexample/example_module/xmsexample_definition.xml',
                'XMS DMI Migration :: DIN :: xmsexample/example_module/xmsexample_migration.din',
            ]
        )

    """
    xml_files = []
    migration_xml_files = []
    for dist in metadata.distributions():
        # check if this package is a DMI interface package
        entry_pt = [x for x in dist.entry_points if x.group == 'xms.dmi.interfaces']
        if len(entry_pt) == 0:
            continue
        if 'classifier' not in dist.metadata.json:
            continue

        # get the path to the distribution.
        for line in dist.metadata.json['classifier']:
            dmi_def = line.startswith('XMS DMI Definition')
            dmi_migration = line.startswith('XMS DMI Migration')
            if not dmi_def and not dmi_migration:
                continue
            cards = line.split(':')
            if len(cards) < 4:
                continue
            the_file = cards[4].strip()
            # prefer call dist.locate_file(xml_file) but it doesn't work with pyproject develop installs
            file_path = str(dist.locate_file(the_file))
            if not os.path.isfile(file_path):
                dist_path = entry_pt[0].load().__path__[0]
                dist_path = os.path.normpath(os.path.join(dist_path, '..', '..'))
                file_path = os.path.normpath(os.path.join(dist_path, the_file))
                if not os.path.isfile(file_path):
                    continue
            if dmi_def:
                xml_files.append(file_path)
            elif dmi_migration:
                migration_xml_files.append(file_path)
    return xml_files, migration_xml_files


def _find_tools() -> dict[str, dict[str, str]]:
    tools_xml_files, _ = find_xms_model_definitions()
    tools = {}
    for file in tools_xml_files:
        tools_tree = Et.parse(file)
        tools_xml = tools_tree.getroot()
        for child in tools_xml:
            tool = {}
            for attribute in child.keys():
                tool[attribute] = child.attrib[attribute]
            tools[tool["uuid"]] = tool
    return tools


class ToolboxTools:
    """
    Manage toolbox tool info.
    """
    tools: dict[str, dict] = _find_tools()

    @classmethod
    def get_tool_list(cls) -> list[dict]:
        """Get the list of tools.

        Returns:
            The list of tools.
        """
        return list(cls.tools.values())

    @classmethod
    def get_run_input(cls, tool_uuid: str) -> Optional[dict[str, Any]]:
        """Build input dictionary for running a tool.

        Args:
            tool_uuid: A string representing the UUID of the tool

        Returns:
            If the tool is found, a dictionary containing the name, module name, class name, and tool UUID of the given
            tool. If the tool is not found, None is returned.
        """
        tool = cls.tools.get(tool_uuid)
        if tool is not None:
            run_input = {
                "name": tool["name"],
                "module_name": tool["module_name"],
                "class_name": tool["class_name"],
                "tool_uuid": tool_uuid
            }
            return run_input
        return None

    @classmethod
    def run_tool(cls, run_input: dict, project_folder: str) -> Optional[dict]:
        """Run a tool.

        Args:
            run_input: A dictionary containing the input data for the tool.
            project_folder: The path to the project folder.

        Returns:
            The results of running the tool, or None if the tool is not found in the list of available tools.
        """
        tool_uuid = run_input['tool_uuid']
        if tool_uuid not in cls.tools:
            print("Unable to find the tool in the list of currently available tools.")
            return

        module_name = run_input['module_name']
        class_name = run_input['class_name']
        module = __import__(module_name, fromlist=[class_name])
        klass = getattr(module, class_name)
        tool = klass()

        tool_name = cls.tools[tool_uuid]["name"]
        send_json = {'tool_name': tool_name, 'tool_description': cls.tools[tool_uuid]['description']}

        if 'arguments' in run_input:
            args = run_input['arguments']
            new_args = []
            for arg in args:
                new_args.append(arg)

            send_json['arguments'] = new_args

        keys = list(run_input.keys())
        for key in keys:
            if key != 'arguments':
                send_json[key] = run_input[key]

        tool.set_gui_data_folder(project_folder)
        tool.project_folder = project_folder
        results = run_tool_dialog(send_json, None, tool)

        if results is not None:
            current_date_time = datetime.now()
            date = current_date_time.strftime("%Y-%m-%d")
            time = current_date_time.strftime("%H:%M:%S")

            results['date'] = date
            results['time'] = time
            results['name'] = tool_name
            results['module_name'] = module_name
            results['class_name'] = class_name
            results['tool_uuid'] = tool_uuid
            results['history_uuid'] = str(uuid.uuid4())

        return results
