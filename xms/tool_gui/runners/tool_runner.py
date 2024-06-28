"""Runs XMS DMI component ActionRequest events."""
# 1. Standard python modules
import argparse
from pathlib import Path
import sys
import traceback
from typing import List

# 2. Third party modules

# 3. Aquaveo modules
try:
    from xms.api.dmi import Query
except ImportError:
    Query = None
from xms.api.dmi import XmsEnvironment
try:
    from xms.components.display import windows_gui as win_gui
except ImportError:
    win_gui = None
from xms.guipy.dialogs.xms_parent_dlg import ensure_qapplication_exists, get_parent_window_container
from xms.tool_gui.tool_dialog import run_tool_dialog

# 4. Local modules


def parse_arguments(args: List[str]) -> argparse.Namespace:
    """Parse arguments for running tool.

    Args:
        args (List[str]): The arguments.

    Returns:
        (argparse.Namespace): The parsed arguments.
    """
    arguments = argparse.ArgumentParser(description="Component method runner.")
    arguments.add_argument(dest='script', type=str, help='script to run')
    arguments.add_argument(dest='module_name', type=str, help='module of the method to run')
    arguments.add_argument(dest='class_name', type=str, help='class of the method to run')
    arguments.add_argument(dest='input_file', type=str, help='file to store tool input')
    arguments.add_argument(dest='output_file', type=str, help='file to store tool output')
    arguments.add_argument(dest='modal_id', type=int, nargs='?', help='modal id of the parent Qt widget')
    arguments.add_argument(dest='main_id', type=int, nargs='?', help='main frame id of XMS')
    parsed_args = arguments.parse_args(args)
    return parsed_args


def main(args):  # noqa: C901
    """Runs the ActionRequest event to run a tool."""
    parsed_args = parse_arguments(args)
    module_name = parsed_args.module_name
    class_name = parsed_args.class_name
    input_file = parsed_args.input_file
    output_file = parsed_args.output_file
    main_id = parsed_args.main_id
    modal_id = parsed_args.modal_id

    query = None
    start_ctxt = None
    if main_id != 0 and Query is not None:
        query = Query()
        query._impl._instance.SetAllowSend(False)
        start_ctxt = query._impl._instance.GetContext()

    accepted = False
    try:
        module = __import__(module_name, fromlist=[class_name])
        klass = getattr(module, class_name)
        tool = klass()

        if modal_id == 0:
            win_cont = None
            accepted = run_tool_dialog(query, input_file, output_file, win_cont, tool)
        else:
            # setup for showing dialog
            ensure_qapplication_exists()
            win_cont = get_parent_window_container(modal_id)
            xms_mainframe_id = 0
            if main_id:
                xms_mainframe_id = int(main_id)
            if win_gui is not None:
                _ = win_gui.create_and_connect_raise_timer(xms_mainframe_id, win_cont)  # Keep the timer in scope

            accepted = run_tool_dialog(query, input_file, output_file, win_cont, tool)

            # tear down for showing dialog
            if win_gui is not None:
                win_gui.raise_main_xms_window(xms_mainframe_id)

    except Exception as ex:
        temp_dir = XmsEnvironment.xms_environ_process_temp_directory()  # Creates it if needed
        debug_file_path = Path(temp_dir) / 'debug_tool_runner.txt'
        with debug_file_path.open('w') as f:
            traceback.print_exception(type(ex), ex, ex.__traceback__, file=f)

    if query is not None:
        query._impl._instance.SetAllowSend(True)
        if not accepted:
            # Don't send back any data that might have been added to the Query by the tool if the user cancels. It is
            # always good to make a send call at the end of the runner script because it helps XMS know that the process
            # exited normally, so make the call but with an empty Context.
            query._impl._instance.SetContext(start_ctxt)
        query.send()
    sys.exit()


# if __name__ == "__main__":
#     sys.argv = ['xms.tool_gui',
#                 'run_tool',
#                 'xms.tool.tools.sample_tools',
#                 'IntegerAdditionTool',
#                 'C:/temp/tool_input.json',
#                 'C:/temp/tool_output.json',
#                 '0',
#                 '0']
#     main(sys.argv[1:])
