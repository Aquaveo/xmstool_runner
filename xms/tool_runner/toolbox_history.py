"""Manage toolbox history."""
import json
import os
from typing import Any, List, Optional, Tuple

from PySide6.QtGui import QIcon, QStandardItem, QStandardItemModel


def resource_path(relative_path: str) -> str:
    """
    Get absolute path to resource file.

    Args:
        relative_path: The relative path of the resource file.

    Returns:
        The full path of the resource file.
    """
    # get path of python file
    path = os.path.join(os.path.dirname(__file__), 'toolbox_icons', relative_path)
    return path


class ToolboxHistory:
    """Manage toolbox history."""

    def __init__(self):
        """Initializes a new instance of the class."""
        self.history = []
        self.model = QStandardItemModel(0, 1)
        self.history_search_model = QStandardItemModel(0, 1)
        self.search_strings_lower = None

    def clear(self) -> None:
        """Clears the history."""
        self.history = []
        self.model.clear()
        self.history_search_model.clear()

    def get_item_description(self, index: int) -> str:
        """
        Get the history item description.

        Args:
            index (int): The index of the item in the history list.

        Returns:
            The concatenated string of "name", "date", and "time" from the item in the history list at the
            specified index.
        """
        history_json: dict[str] = self.history[index]
        date = history_json["date"]
        time = history_json["time"]
        name = history_json["name"]
        return name + " " + date + " " + time

    def get_model(self) -> QStandardItemModel:
        """
        Returns the history model.

        Returns:
            The history model.
        """
        return self.model

    def add_item(self, history: dict[str, Any]) -> int:
        """
        Add an item to the history list and return the index of the added item.

        Args:
            history: The JSON object representing the item to be added to the history.

        Returns:
            int: The index of the added item.

        Note:
            If the history does not contain the 'notes' key, it will be added with the description obtained from
            'get_item_description' method using the index of the added item in the history list.
        """
        history_index = len(self.history)
        self.history.append(history)
        new_item = self.history[-1]
        if "notes" not in new_item:
            new_item["notes"] = self.get_item_description(len(self.history) - 1)
        self._add_to_model(history_index)
        return history_index

    def delete_item(self, history_uuid: str):
        """
        Deletes an item from the history.

        Args:
            history_uuid: The UUID of the item to delete.
        """
        index = self.get_history_index_from_uuid(history_uuid)
        if index is not None:
            for row in range(self.model.rowCount()):
                date_item = self.model.item(row)
                if date_item:
                    for description_row in range(date_item.rowCount()):
                        compare_item = date_item.child(description_row)
                        if compare_item is not None and compare_item.data == history_uuid:
                            del date_item[description_row]
                            break
                    if date_item.rowCount() == 0:
                        self.model.removeRow(row)
            del self.history[index]

    def _get_item_data(self, index: int):
        """
        Gets item data from the history based on the specified index.

        Args:
            index (int): The index of the item in the history.

        Returns:
            tuple: A tuple containing the following item data:
                - date (str): The date of the item.
                - description (str): The description of the item.
                - history_uuid (str): The UUID of the history.
                - notes (str): The notes of the item.
                - arguments (list): The extracted arguments of the item.
                - output (str): The extracted output of the item.
                - run_status (str): The run status of the item.
        """
        history_json = self.history[index]
        date = history_json["date"]
        description = self.get_item_description(index)
        history_uuid = history_json["history_uuid"]
        notes = history_json["notes"]

        arguments = _extract_arguments(history_json)
        output, run_status = _extract_output(history_json)

        return date, description, history_uuid, notes, arguments, output, run_status

    def _add_to_model(self, history_index: int) -> None:
        """
        Add the history for a given index to the model.

        Args:
            history_index:
                The index of the history item to be added to the model.
        """
        date, description, uuid, notes, arguments, output, run_status = self._get_item_data(history_index)
        date_item = _get_date_item(self.model, date)
        history_item = _add_notes(notes, uuid, run_status, date_item)

        input_item = _create_input_items(arguments, uuid)
        history_item.appendRow(input_item)

        if output:
            output_item = _create_output_items(output, description, uuid)
            history_item.appendRow(output_item)

    def set_search_strings(self, search_strings: List[str]) -> None:
        """
        Update the search model for the given search strings.

        Args:
            search_strings: A list of strings containing the search keywords.
        """
        self.search_strings_lower = [search_string.lower() for search_string in search_strings]
        self._update_search_model()

    def _update_search_model(self) -> None:
        """
        Updates the search model for the history view.

        This method clears the search model for the history view and populates it with filtered data based on the search
        strings.
        """
        self.history_search_model.clear()
        num_history = len(self.history)
        for i in range(num_history):
            date, description, uuid, notes, arguments, output, run_status = self._get_item_data(i)
            input_item = None
            output_item = None

            for argument in arguments:
                if string_matches_search(argument, self.search_strings_lower):
                    if not input_item:
                        input_item = _add_line_item("Input:", uuid, resource_path("tool_history_output_item.svg"))
                    _add_line_item(argument, uuid, resource_path("tool_history_arg_item.png"), input_item)

            if output:
                if string_matches_search(description, self.search_strings_lower):
                    if not output_item:
                        output_item = _add_line_item("Output:", uuid, resource_path("tool_history_output_item.svg"))
                    _add_line_item(description, uuid, "", output_item)
                for line in output:
                    if string_matches_search(line, self.search_strings_lower):
                        if not output_item:
                            output_item = _add_line_item("Output:", uuid, resource_path("tool_history_output_item.svg"))
                        _add_line_item(line, uuid, "", output_item)

            if string_matches_search(notes, self.search_strings_lower) or input_item or output_item:
                date_item = _get_date_item(self.history_search_model, date)
                history_item = _add_notes(notes, uuid, run_status, date_item)
                if input_item:
                    history_item.appendRow(input_item)
                if output_item:
                    history_item.appendRow(output_item)

    def get_history_index_from_uuid(self, history_uuid: str) -> Optional[int]:
        """
        Get the index of the history item.

        Args:
            history_uuid: The UUID of the history item you want to find the index for.

        Returns:
            The index of the history item if found, or None if no item with the specified UUID exists.
        """
        for count, item in enumerate(self.history):
            if item['history_uuid'] == history_uuid:
                return count
        return None

    def get_run_input(self, history_uuid: str) -> Optional[dict]:
        """
        Get input for running a tool from a history item.

        Args:
            history_uuid: The UUID of the history item.

        Returns:
            The run input associated with the given history UUID, or None if not found.
        """
        index = self.get_history_index_from_uuid(history_uuid)
        if index is not None:
            run_input = self.history[index]
            return run_input
        return None

    def read_history_file(self, project_folder: str) -> None:
        """
        Reads the history data from a JSON file.

        Args:
            project_folder: The path to the project folder.
        """
        self.clear()
        history_file = os.path.join(project_folder, "history.json")
        if os.path.exists(history_file):
            with open(history_file, 'r') as file:
                new_history = json.load(file)
                for item in new_history:
                    self.add_item(item)

    def write_history_file(self, project_folder: str) -> None:
        """
        Writes the history data to a JSON file.

        Args:
            project_folder: The path to the project folder.
        """
        history_file = os.path.join(project_folder, "history.json")
        with open(history_file, 'w') as file:
            json.dump(self.history, file, indent=4)


def _add_line_item(text: str,
                   data: Any,
                   icon: str = "",
                   a_parent: Optional[QStandardItem] = None,
                   editable: bool = False) -> QStandardItem:
    """
    Add a model line item.

    Args:
        text: The text to be displayed for the line item.
        data: The data to be associated with the line item.
        icon: The optional icon to be displayed next to the line item.
        a_parent: The optional parent item under which the line item should be added.
        editable: The optional flag indicating whether the line item should be editable.

    Returns:
        The created QStandardItem object representing the line item.
    """
    line_item = QStandardItem(text)
    line_item.setData(data)
    line_item.setEditable(editable)
    if icon:
        line_item.setIcon(QIcon(icon))
    if a_parent:
        a_parent.appendRow(line_item)
    return line_item


def _get_date_item(model: QStandardItemModel, date: str) -> QStandardItem:
    """
    Retrieve or create a date item from the model.

    Args:
        model: The QStandardItemModel object representing the model where the date item will be searched and added.
        date: The string representing the date item that needs to be retrieved or created.

    Returns:
        QStandardItem: The QStandardItem object representing the retrieved or created date item.
    """
    date_item = None
    # search for existing date item
    for row in range(model.rowCount()):
        compare_to_item = model.item(row, 0)
        if compare_to_item and compare_to_item.text() == date:
            # found existing date item
            date_item = compare_to_item
            break

    if not date_item:
        date_item = _add_line_item(date, "", resource_path("tool_date_history_item.svg"))
        model.appendRow(date_item)
    return date_item


def _add_notes(notes: str, history_uuid: str, ran_successfully: bool, parent: QStandardItem) -> QStandardItem:
    """
    Add notest to a history item.

    Args:
        notes: The notes to be added to the history item.
        history_uuid: The unique identifier for the history item.
        ran_successfully: Use success icon or failure icon.
        parent: The parent item of the history item.

    Returns:
        The new notes item.
    """
    item_icon = resource_path("tool_history_item_success.svg")
    if not ran_successfully:
        item_icon = resource_path("tool_history_item_failure.svg")
    return _add_line_item(notes, history_uuid, item_icon, parent, True)


def _extract_arguments(history_json: dict) -> list[str]:
    """
    Extract list of arguments from history JSON.

    Args:
        history_json: The JSON object representing the history.

    Returns:
        arguments: A list of string representations of the arguments extracted from the history JSON.
    """
    arguments = []
    if "arguments" in history_json:
        array = history_json["arguments"]
        for i in range(len(array)):
            cur_obj = array[i]
            arg_name = cur_obj["name"]
            arg_value = cur_obj.get("value", "")
            arg_text = f"{arg_name}: {arg_value}"
            arguments.append(arg_text)
    return arguments


def _extract_output(history_json: dict) -> Tuple[list[str], bool]:
    """
    Extracts the output and run status from a given history JSON.

    Args:
        history_json: The JSON containing the execution history.

    Returns:
        (output, run_status): A tuple containing the extracted output and run status.
    """
    run_status = False
    output = []
    if "status" in history_json:
        status = history_json["status"]
        output.append(f"Run status: {status}")
        if status.lower() == "success":
            run_status = True
    if "output" in history_json:
        output_list = history_json["output"].split('\n')
        for line in output_list:
            if line.startswith("$XMS_BOLD$"):
                line = line[len("$XMS_BOLD$"):]
            if line.startswith("$XMS_LEVEL$"):
                line = line[len("$XMS_LEVEL$"):]
            output.append(line)

        # remove empty lines at end of output
        while output and not output[-1].strip():
            output.pop()
    return output, run_status


def _create_output_items(output: list[str], description: str, uuid: str) -> QStandardItem:
    """
    Create history output items.

    Args:
        output: The list of lines to be included in the output item.
        description: The description for the output item.
        uuid: The UUID for the output item.

    Returns:
        The output item that is created.
    """
    output_item = _add_line_item("Output:", uuid, resource_path("tool_history_output_item.svg"))
    _add_line_item(description, uuid, "", output_item)
    for line in output:
        _add_line_item(line, uuid, "", output_item)
    return output_item


def _create_input_items(arguments: list[str], uuid: str):
    """
    Create history input items.

    Args:
        arguments: List of arguments.
        uuid: The uuid of the history item.
    """
    input_item = _add_line_item("Input:", uuid, resource_path("tool_history_output_item.svg"))
    for argument in arguments:
        _add_line_item(argument, uuid, resource_path("tool_history_arg_item.png"), input_item)
    return input_item


def string_matches_search(string: str, search_strings_lower: List[str]) -> bool:
    """
    Determine if a string matches a list of search strings.

    Args:
        string: The input string to be checked.
        search_strings_lower: The list of lower-cased search strings.

    Returns:
        bool: True if all search strings are found in the lower-cased input string, False otherwise.
    """
    str_lower = string.lower()
    for search_string in search_strings_lower:
        if search_string not in str_lower:
            return False
    return True
