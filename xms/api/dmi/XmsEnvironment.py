"""Python wrapping for xms.api._xmsapi.dmi.Query."""
# 1. Standard python modules
import datetime
import os
import tempfile
import traceback

# 2. Third party modules

# 3. Aquaveo modules
from xms.core.filesystem import filesystem as io_util

# 4. Local modules

# Environment variables set by XMS
ENVIRON_XMS_TEMP_FOLDER = 'XMS_PYTHON_APP_TEMP_DIRECTORY'
ENVIRON_PROCESS_TEMP_FOLDER = 'XMS_PYTHON_APP_PROCESS_TEMP_DIRECTORY'
ENVIRON_PROCESS_GLOBAL_TIMES = 'XMS_PYTHON_APP_PROCESS_GLOBAL_TIMES'
ENVIRON_XMS_SHARED_FOLDER = 'XMS_PYTHON_APP_SHARED_DIRECTORY'
ENVIRON_XMS_APP_NAME = 'XMS_PYTHON_APP_NAME'
ENVIRON_XMS_APP_VERSION = 'XMS_PYTHON_APP_VERSION'
ENVIRON_XMS_PROJECT_VERSION = 'XMS_PYTHON_PROJECT_VERSION'
ENVIRON_NOTES_DATABASE = 'XMS_PYTHON_APP_NOTES_DATABASE'
ENVIRON_PROJECT_PATH = 'XMS_PYTHON_APP_PROJECT_PATH'
ENVIRON_RUNNING_TESTS = 'XMS_PYTHON_APP_RUNNING_TESTS'
ENVIRON_XMS_APP_PID = 'XMS_PYTHON_APP_PID'
ENVIRON_XMS_STD_ERR_FILE = 'XMS_PYTHON_STD_ERR_FILE'
ENVIRON_XMS_STD_OUT_FILE = 'XMS_PYTHON_STD_OUT_FILE'
ENVIRON_XMS_RECORD_TRIGGER_FILE = 'XMS_PYTHON_RECORD_TRIGGER_FILE'
ENVIRON_XMS_PLAYBACK_RECORD_FILE = 'XMS_PLAYBACK_RECORD_FILE'
ENVIRON_XMS_LOGGING_BASE_FILE = 'XMS_LOGGING_BASE_FILE'
ENVIRON_XMS_LOGGING_OUT_FILE = 'XMS_LOGGING_OUT_FILE'
ENVIRON_XMS_SENT_DATA_BASE_FILE = 'XMS_SENT_DATA_BASE_FILE'
ENVIRON_XMS_SENT_DATA_OUT_FILE = 'XMS_SENT_DATA_OUT_FILE'
ENVIRON_XMS_PLAYBACK_FOLDER = 'XMS_PLAYBACK_FOLDER'

# Predefined error states
EXPORT_ERROR_OCCURRED = 'ERROR_LOGGED_WITH_SIMULATION_SAVE'
EXPORT_USER_CANCELLED = 'USER_CANCEL_SAVE'

# Query playback/record files and environment variables
ENVIRON_FORCE_RECORD = 'XMS_PYTHON_RECORD'  # Set to a recording folder to force next Query created to be in record mode
RECORD_TRIGGER_FILE = 'C:/temp/query_record.dbg'  # Next Query created will be in record or playback mode if file exists
PLAYBACK_RECORD_FILE = 'request.rec'  # Created in record mode, read in playback mode
LOGGING_BASE_FILE = 'logging.base'
LOGGING_OUT_FILE = 'logging.out'
SENT_DATA_BASE_FILE = 'sent_data.base'  # Created in record mode, compared to output in playback mode
SENT_DATA_OUT_FILE = 'sent_data.out'  # Created and compared to baseline in playback mode


def xms_environ_record_trigger_file():
    """Returns the XMS record trigger file used by QueryPlayback."""
    return os.environ.get(ENVIRON_XMS_RECORD_TRIGGER_FILE, RECORD_TRIGGER_FILE)


def xms_environ_playback_record_file():
    """Returns the XMS playback record file used by QueryPlayback."""
    return os.environ.get(ENVIRON_XMS_PLAYBACK_RECORD_FILE, PLAYBACK_RECORD_FILE)


def xms_environ_logging_base_file():
    """Returns the XMS logging base file used by QueryPlayback."""
    return os.environ.get(ENVIRON_XMS_LOGGING_BASE_FILE, LOGGING_BASE_FILE)


def xms_environ_logging_out_file():
    """Returns the XMS logging out file used by QueryPlayback."""
    return os.environ.get(ENVIRON_XMS_LOGGING_OUT_FILE, LOGGING_OUT_FILE)


def xms_environ_sent_data_base_file():
    """Returns the XMS sent data base file used by QueryPlayback."""
    return os.environ.get(ENVIRON_XMS_SENT_DATA_BASE_FILE, SENT_DATA_BASE_FILE)


def xms_environ_sent_data_out_file():
    """Returns the XMS sent data out file used by QueryPlayback."""
    return os.environ.get(ENVIRON_XMS_SENT_DATA_OUT_FILE, SENT_DATA_OUT_FILE)


# Global functions for getting environment variables set by XMS. Allows code to
# access without constructing a Query object.
def xms_environ_temp_directory():
    """Returns the XMS temp directory or system temp if not set."""
    return os.environ.get(ENVIRON_XMS_TEMP_FOLDER, tempfile.gettempdir())


def xms_environ_shared_directory():
    """Returns the shared component data folder in the XMS temp directory. Creates if it doesn't exist."""
    shared_folder = os.environ.get(ENVIRON_XMS_SHARED_FOLDER, tempfile.gettempdir())
    os.makedirs(shared_folder, exist_ok=True)  # Ensure the folder exists
    return shared_folder


def xms_environ_process_temp_directory():
    """Returns the temp directory that is deleted when this process ends. Creates if it doesn't exist."""
    process_temp = os.environ.get(ENVIRON_PROCESS_TEMP_FOLDER, tempfile.gettempdir())
    os.makedirs(process_temp, exist_ok=True)  # Ensure the folder exists
    return process_temp


def xms_environ_process_global_times():
    """Returns the currently available global timesteps.

    Returns:
        list: list of datetime.datetime objects if the timesteps are absolute
    """
    global_times_file = os.environ.get(ENVIRON_PROCESS_GLOBAL_TIMES, '')
    global_times = []
    if os.path.isfile(global_times_file):
        with open(global_times_file, 'r') as f:
            lines = f.read().splitlines()
        if lines:
            try:  # If relative, float offset in seconds
                global_times = [datetime.timedelta(seconds=float(line)) for line in lines if line]
            except Exception:  # If absolute, in %Y-%m-%d %H:%M:%S format
                global_times = [datetime.datetime.fromisoformat(line) for line in lines if line]
    return global_times


def xms_environ_app_name():
    """Name of the XMS app that launched the script."""
    return os.environ.get(ENVIRON_XMS_APP_NAME, '')


def xms_environ_app_version():
    """Version of the XMS app up to the minor version that launched the script."""
    return os.environ.get(ENVIRON_XMS_APP_VERSION, '')


def xms_environ_project_version():
    """Version of the XMS project file up to the minor version, or 0.0 if currently unsaved."""
    return os.environ.get(ENVIRON_XMS_PROJECT_VERSION, '0.0')


def xms_environ_notes_database():
    """Path to the XMS notes database."""
    return os.environ.get(ENVIRON_NOTES_DATABASE, '')


def xms_environ_project_path():
    """Path to the saved XMS project currently loaded or empty string if unsaved."""
    return os.environ.get(ENVIRON_PROJECT_PATH, '')


def xms_environ_running_tests():
    """Returns 'TRUE' if XMS is currently running tests."""
    return os.environ.get(ENVIRON_RUNNING_TESTS, '')


def xms_environ_stdout_file():
    """Returns the path to the process's stdout echo file, if there is one."""
    return os.environ.get(ENVIRON_XMS_STD_OUT_FILE, '')


def xms_environ_debug_file():
    """Returns the path to the process's debug echo file."""
    return os.path.join(xms_environ_temp_directory(), 'python_debug.log')


def xms_environ_playback_folder():
    """Returns the path to the process's playback folder, if there is one."""
    return os.environ.get(ENVIRON_XMS_PLAYBACK_FOLDER, '')


# Methods for reporting error states/messages to XMS when script has no or limited feedback mechanism.
def report_error(error, log_file=None):
    """Report an error to XMS that will show up in an popup GUI message.

    Args:
        error (Union[str, Exception]): The error message or exception to report
        log_file (str): Path to the log file. By default, will be written to the XMS-specified stderr file used to
            report errors to the user in XMS for scripts that do not have good feedback mechanisms.
    """
    log_file = log_file if log_file else os.environ.get(ENVIRON_XMS_STD_ERR_FILE, io_util.temp_filename())
    with open(log_file, 'a') as f:
        if isinstance(error, Exception):
            traceback.print_exception(type(error), error, error.__traceback__, file=f)
            f.write('\n')
        else:
            f.write(f'{error}\n')


def report_export_error():
    """Report an error that indicates to XMS that a simulation export failed."""
    with open(os.environ.get(ENVIRON_XMS_STD_ERR_FILE, io_util.temp_filename()), 'a') as f:
        f.write(f'{EXPORT_ERROR_OCCURRED}\n')


def report_export_aborted():
    """Report that a simulation export was aborted by the user - no error."""
    with open(os.environ.get(ENVIRON_XMS_STD_ERR_FILE, io_util.temp_filename()), 'a') as f:
        f.write(f'{EXPORT_USER_CANCELLED}\n')
