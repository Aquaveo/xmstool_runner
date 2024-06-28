"""Reader for ADCIRC solution output files."""
# 1. Standard python modules
import copy
import math
import os
import uuid

# 2. Third party modules
import netCDF4
import numpy as np

# 3. Aquaveo modules
from xms.data_objects.parameters import Dataset, datetime_to_julian
from xms.datasets.dataset_writer import DatasetWriter

# 4. Local modules
from xms.adcirc.feedback.xmlog import XmLog


ADCIRC_NULL_VALUE = -99999.0
# Need to skip these files, they are time series curves at recording station locations.
NETCDF_STATIONS = ['fort.61.nc', 'fort.62.nc', 'fort.71.nc', 'fort.72.nc']
ASCII_STATIONS = ['fort.61', 'fort.62', 'fort.71', 'fort.72']
IO_BUFFER_SIZE = 100000


class ADCIRCSolutionReader:
    """The ADCIRC solution file reader."""
    def __init__(self, filenames, reftime, query, temp_dir, geom_uuid='CCCCCCCC-CCCC-CCCC-CCCC-CCCCCCCCCCCC'):
        """Construct the reader.

        Args:
            filenames (:obj:`list`): List of the filenames (with paths) to read
            reftime (:obj:`datetime.datetime`): Simulation start time
            query (:obj:`Query`): Object for communicating with XMS
            temp_dir (:obj:`str`): Path to the XMS temp directory. This is where we will write the converted XMDF
                solution files
            geom_uuid (:obj:`str`): UUID of the solution datasets' geometry, if known. Otherwise, XMS will try to
                match based on number of values but can go to the wrong geometry if it matches.
        """
        self.query = query
        self.temp_dir = temp_dir
        self.reftime = datetime_to_julian(reftime)  # Used for reference time on transient datasets, convert to Julian.
        self.geom_uuid = geom_uuid  # Used to link datasets to a known geometry. Otherwise, SMS will look for a match.
        self.filenames = filenames  # List of solution files to read
        self.num_ts = 0
        self.num_nodes = 0
        self.read_file = ""
        self.read_data = False
        self.out_filename = None  # For testing
        self.dset_uuid = None  # For testing
        self.overwrite_files = True  # For testing

    def _get_next_h5_filename_and_uuid(self):
        """Either get a random UUID and filename of an H5 file to write from the Query or hardcoded list if testing.

        Returns:
            (:obj:`tuple(str, str)`): Filesystem path to use to write an H5 file, UUID for the dataset
        """
        if self.out_filename and self.dset_uuid:
            return self.out_filename, self.dset_uuid
        else:  # pragma: no cover
            dset_uuid = str(uuid.uuid4())
            return os.path.join(self.temp_dir, f'{dset_uuid}.h5'), dset_uuid

    def _get_dataset_writer(self, dset_name, num_components):
        """Get a dataset writer for appending timesteps.

        Args:
            dset_name (:obj:`str`): Tree item name of the dataset to create in SMS.
            num_components (:obj:`int`): 1 = scalar, 2 = 2D vector

        Returns:
            DatasetWriter: The initialized dataset writer
        """
        xmdf_filename, dset_uuid = self._get_next_h5_filename_and_uuid()
        writer = DatasetWriter(h5_filename=xmdf_filename, name=dset_name, dset_uuid=dset_uuid, geom_uuid=self.geom_uuid,
                               null_value=ADCIRC_NULL_VALUE, ref_time=self.reftime, time_units='Seconds',
                               num_components=num_components, overwrite=self.overwrite_files)
        return writer

    def _write_xmdf_dataset(self, dset_name, times, data, num_components):
        """Write a solution dataset to an XMDF formatted file that XMS can read.

        Args:
            dset_name (:obj:`str`): Tree item name of the dataset to create in SMS.
            times (:obj:`Sequence`): 1-D array of float time step offsets
            data (:obj:`Sequence`): The dataset values organized in XMDF structure. Rows are timesteps and columns are
                node/cell values. If a vector dataset, outer dimensions contain the additional components.
            num_components (:obj:`int`): 1 = scalar, 2 = 2D vector
        """
        xmdf_filename, dset_uuid = self._get_next_h5_filename_and_uuid()
        writer = DatasetWriter(h5_filename=xmdf_filename, name=dset_name, dset_uuid=dset_uuid, geom_uuid=self.geom_uuid,
                               null_value=ADCIRC_NULL_VALUE, ref_time=self.reftime, time_units='Seconds',
                               num_components=num_components, overwrite=self.overwrite_files)
        writer.write_xmdf_dataset(times, data)
        self.add_xmdf_dataset(xmdf_filename, dset_name)

    def read_ascii_max_scalars(self, f, name):
        """Reads a max*.63 solution datasets.

        For the maxele.63 and maxvel.63, the first "time step" is the maximum WSE/velocity. The second "time step" is
        the time at which the maximum was reached.

        Args:
            f: Open file handle to the max*.63 ASCII file. Should be at beginning of file.
            name (:obj:`str`): Name of the dataset. A second dataset will be created with " Time" appended to its name.
        """
        dset_vals = []
        times = []

        try:
            self.read_header(f)

            for i in range(2):  # Two steady-state datasets in these files formatted as separate time steps.
                # get the timestep time
                ts_line = f.readline()
                if not ts_line or not ts_line.strip():
                    break  # reached unexpected EOF

                ts_line = ts_line.split()
                ts_time = float(ts_line[0])

                ts_vals = [0.0 for _ in range(self.num_nodes)]

                # Read in the values for this timestep
                add_dset = True
                for j in range(self.num_nodes):
                    node_line = f.readline()
                    if not node_line or not node_line.strip():
                        add_dset = False  # not enough values for this timestep
                        break  # reached unexpected EOF, probably won't be able to recover

                    node_line = node_line.split()
                    ts_vals[j] = float(node_line[1])

                # add the timestep if enough values were written to the output
                if add_dset:
                    dset_vals.append(copy.deepcopy(ts_vals))
                    times.append(ts_time)
                    if i > 0:
                        name += ' Time'  # The second "time step" is the maximum time dataset
                    self._write_xmdf_dataset(name, times, dset_vals, 1)
                dset_vals = []  # Reset data dict for next dataset (time step)
                times = []
        except Exception:
            # This is not a great solution. We just fail silently anytime there is a problem,
            # but the user may have exported some output in binary (not netCDF) and we do not
            # support ADCIRC's in-house binary format. We still want to read other output files
            # though.
            pass  # CHANGE TO raise IF YOU NEED TO DEBUG

    def read_ascii_scalars(self, file, name):
        """Read a scalar dataset from an ASCII file.

        Args:
            file: Open stream to the file to read
            name (:obj:`str`): Name to assign to the imported dataset.
        """
        read_data = False
        try:
            writer = self._get_dataset_writer(dset_name=name, num_components=1)
            self.read_header(file)

            for i in range(self.num_ts):  # loop through the timesteps
                XmLog().instance.info(f'Reading timestep {i + 1} of {self.num_ts}')
                # get the timestep time
                ts_line = file.readline()
                if not ts_line or not ts_line.strip():
                    break  # reached unexpected EOF

                ts_line = ts_line.split()
                ts_time = float(ts_line[0])

                default_val = 0.0
                num_vals = self.num_nodes
                sparse = False
                if len(ts_line) > 3:  # if sparse, there will be more on this line
                    num_vals = int(ts_line[2])  # adjust num_vals
                    default_val = float(ts_line[3])
                    sparse = True

                ts_vals = [default_val for _ in range(self.num_nodes)]

                # Read in the values for this timestep
                add_timestep = True
                for j in range(num_vals):
                    node_line = file.readline()
                    if not node_line or not node_line.strip():
                        add_timestep = False  # not enough values for this timestep
                        break  # reached unexpected EOF

                    node_line = node_line.split()
                    if sparse:
                        node_id = int(node_line[0])
                        ts_vals[node_id - 1] = float(node_line[1])
                    else:
                        ts_vals[j] = float(node_line[1])

                # add the timestep if enough values were written to the output
                if add_timestep:
                    read_data = True
                    writer.append_timestep(time=ts_time, data=ts_vals)

            if read_data:
                writer.appending_finished()
                self.add_xmdf_dataset(writer.h5_filename, writer.name)
        except Exception:
            XmLog().instance.exception(f'Error reading solution file: {self.read_file}')

    def read_ascii_vectors(self, file, name):
        """Read a vector dataset from an ASCII file.

        Args:
            file: Open stream to the file to read
            name (:obj:`str`): Name to assign to the imported dataset.
        """
        read_data = False
        try:
            writer = self._get_dataset_writer(dset_name=name, num_components=2)
            self.read_header(file)

            for i in range(self.num_ts):  # loop through the timesteps
                XmLog().instance.info(f'Reading timestep {i + 1} of {self.num_ts}')
                # get the timestep time
                ts_line = file.readline()
                if not ts_line or not ts_line.strip():
                    break  # reached unexpected EOF

                ts_line = ts_line.split()
                ts_time = float(ts_line[0])

                default_val1 = 0.0
                default_val2 = 0.0
                num_vals = self.num_nodes
                sparse = False
                if len(ts_line) > 2:  # if sparse, there will be more on this line
                    num_vals = int(ts_line[2])  # adjust num_vals
                    default_val1 = float(ts_line[3])
                    default_val2 = float(ts_line[4])
                    sparse = True

                ts_vals = [[default_val1, default_val2] for _ in range(self.num_nodes)]

                # Read in the values for this timestep
                add_timestep = True
                for j in range(num_vals):
                    node_line = file.readline()
                    if not node_line or not node_line.strip():
                        add_timestep = False  # not enough values for this timestep
                        break  # reached unexpected EOF

                    node_line = node_line.split()
                    if sparse:
                        node_id = int(node_line[0])
                        ts_vals[node_id - 1] = [float(node_line[1]), float(node_line[2])]
                    else:
                        ts_vals[j] = [float(node_line[1]), float(node_line[2])]

                # add the timestep if enough values were written to the output
                if add_timestep:
                    read_data = True
                    writer.append_timestep(time=ts_time, data=ts_vals)

            if read_data:
                writer.appending_finished()
                self.add_xmdf_dataset(writer.h5_filename, writer.name)
        except Exception:
            # This is not a great solution. We just fail silently anytime there is a problem,
            # but the user may have exported some output in binary (not netCDF) and we do not
            # support ADCIRC's in-house binary format. We still want to read other output files
            # though.
            pass  # CHANGE TO raise IF YOU NEED TO DEBUG

    def read_ascii_harmonic(self, f_in, scalar=True):
        """Read an ASCII format harmonic analysis solution dataset (fort.53/54) file.

        Args:
            f_in: Open file handle to the fort.53/54. Should be at position 0.
            scalar (:obj:`bool`, optional): True if this is a scalar dataset file (fort.53), False otherwise (fort.54).
        """
        # Read the number of constituents in the analysis
        num_cons = int(f_in.readline().split()[0])
        con_names = ["" for _ in range(num_cons)]
        # Read the constituent names
        for i in range(num_cons):
            # TODO: Do we care about HAFREQ(k), HAFF(k), HAFACE(k) on this line?
            con_names[i] = f_in.readline().split()[3]
        # Read the number of points.
        num_pts = int(f_in.readline().split()[0])

        # Allocate arrays for dataset values
        amp_mag = []
        phase_mag = []
        if scalar:
            amp_values = [[0.0 for _ in range(num_pts)] for _ in range(num_cons)]
            phase_values = [[0.0 for _ in range(num_pts)] for _ in range(num_cons)]
        else:
            amp_values = [[[0.0, 0.0] for _ in range(num_pts)] for _ in range(num_cons)]
            phase_values = [[[0.0, 0.0] for _ in range(num_pts)] for _ in range(num_cons)]
            amp_mag = [[0.0 for _ in range(num_pts)] for _ in range(num_cons)]
            phase_mag = [[0.0 for _ in range(num_pts)] for _ in range(num_cons)]

        for i in range(num_pts):
            f_in.readline()  # Node id
            for j in range(num_cons):
                line = f_in.readline().split()
                if scalar:
                    # Read the elevation scalar for amplitude and phase.
                    amp_values[j][i] = float(line[0])
                    phase_values[j][i] = float(line[1])
                else:
                    # Read the x and y vector components for amplitude and phase.
                    amp_values[j][i][0] = float(line[0])
                    amp_values[j][i][1] = float(line[2])
                    phase_values[j][i][0] = float(line[1])
                    phase_values[j][i][1] = float(line[3])
                    # Compute the vector magnitude
                    amp_mag[j][i] = math.sqrt(amp_values[j][i][0]**2 + amp_values[j][i][1]**2)
                    phase_mag[j][i] = math.sqrt(phase_values[j][i][0]**2 + phase_values[j][i][1]**2)

        # add the solution datasets to the Context.
        num_components = 1 if scalar else 2
        for i in range(num_cons):
            dset_type = " Elevation " if scalar else " Velocity "
            self._write_xmdf_dataset(con_names[i] + dset_type + "Amplitude", [0.0], [amp_values[i]], num_components)
            self._write_xmdf_dataset(con_names[i] + dset_type + "Phase", [0.0], [phase_values[i]], num_components)
            # add the vector magnitude datasets when appropriate.
            if not scalar:
                self._write_xmdf_dataset(con_names[i] + dset_type + "Amplitude Magnitude", [0.0], [amp_mag[i]], 1)
                self._write_xmdf_dataset(con_names[i] + dset_type + "Phase Magnitude", [0.0], [phase_mag[i]], 1)

    def read_netcdf_scalars(self, filename, scalar_path, dset_name):
        """Read a scalar solution dataset from a NetCDF formatted file.

        Args:
            filename (:obj:`str`): Filesystem path to the NetCDF solution file.
            scalar_path (:obj:`str`): Path in the NetCDF file to the solution dataset
            dset_name (:obj:`str`): Tree item name of the dataset to create in SMS.
        """
        root_grp = netCDF4.Dataset(filename, "r", format="NETCDF4_CLASSIC")
        scalar_data = root_grp[scalar_path][:]
        if scalar_data.size == 0:
            XmLog().instance.warning(  # Only print the file's entire path if we aren't testing.
                f'Empty solution data set encountered: {os.path.basename(filename) if self.out_filename else filename}'
            )
            return  # No data to write in the file

        # Replace -99999.0 null values with NaN for numpy operations.
        scalar_data[scalar_data == ADCIRC_NULL_VALUE] = np.nan

        # Convert numpy NaNs back to null value for XMDF file.
        scalar_data[np.isnan(scalar_data)] = ADCIRC_NULL_VALUE

        # Write the XMDF file
        self._write_xmdf_dataset(dset_name, root_grp["/time"][:], scalar_data, 1)

    def read_netcdf_vectors(self, filename, x_path, y_path, dset_name):
        """Read a vector solution dataset from a NetCDF formatted file.

        Args:
            filename (:obj:`str`): Filesystem path to the NetCDF solution file.
            x_path (:obj:`str`): Path in the NetCDF file to the x-component solution dataset
            y_path (:obj:`str`): Path in the NetCDF file to the y-component solution dataset
            dset_name (:obj:`str`): Tree item name of the dataset to create in SMS.
        """
        # Read the x and y component values from the NetCDF solution file.
        root_grp = netCDF4.Dataset(filename, "r", format="NETCDF4_CLASSIC")
        x_data = root_grp[f"{x_path}"][:]
        y_data = root_grp[f"{y_path}"][:]

        if x_data.size == 0:
            XmLog().instance.warning(  # Only print the file's entire path if we aren't testing.
                f'Empty solution data set encountered: {os.path.basename(filename) if self.out_filename else filename}'
            )
            return  # No data to write in the file

        # Replace -99999.0 and 0.0 null values with NaN for numpy operations.
        x_data[x_data == ADCIRC_NULL_VALUE] = np.nan
        y_data[y_data == ADCIRC_NULL_VALUE] = np.nan

        # Create an XMDF-style data cube of the vector components. Shape=(num_times, num_vals, 2)
        vector_data = np.stack([x_data, y_data], axis=2)

        # Convert numpy NaNs back to null value for XMDF file.
        vector_data[np.isnan(vector_data)] = ADCIRC_NULL_VALUE

        # Write the XMDF file
        self._write_xmdf_dataset(dset_name, root_grp['/time'][:], vector_data, 2)

    def read_netcdf_max_scalars(self, filename, scalar_path, time_path, dset_name):
        """Read an extreme dataset (min/max) from a NetCDF formatted file.

        Args:
            filename (:obj:`str`): Filesystem path to the NetCDF solution file.
            scalar_path (:obj:`str`): Path in the NetCDF file to the "extreme" solution dataset
            time_path (:obj:`str`): Path in the NetCDF file to the "time of extreme" solution dataset
            dset_name (:obj:`str`): Tree item name of the dataset to create in SMS.
        """
        root_grp = netCDF4.Dataset(filename, "r", format="NETCDF4_CLASSIC")
        extreme_grp = root_grp[f"{scalar_path}"][:]
        if extreme_grp.size == 0:
            XmLog().instance.warning(  # Only print the file's entire path if we aren't testing.
                f'Empty solution data set encountered: {os.path.basename(filename) if self.out_filename else filename}'
            )
            return  # No data to write in the file
        extreme_dset_data = [float(x) if x else ADCIRC_NULL_VALUE for x in extreme_grp]
        self._write_xmdf_dataset(dset_name, [0.0], [extreme_dset_data], 1)
        time_grp = root_grp[f"{time_path}"][:]
        time_dset_data = [float(x) if x else ADCIRC_NULL_VALUE for x in time_grp]
        self._write_xmdf_dataset(dset_name + ' Time', [0.0], [time_dset_data], 1)

    def add_xmdf_dataset(self, filename, dset_name):
        """Add an existing XMDF dataset file to the Query to read into XMS.

        Args:
            filename (:obj:`str`): Filepath to the XMDF dataset
            dset_name (:obj:`str`): Name of the dataset. Used to build the HDF5 path to the dataset.
        """
        dset = Dataset(filename, f'Datasets/{dset_name}', 'NODE', 'NODE')
        if self.query:  # pragma: no cover
            folder_path = 'Extremes' if dset_name.startswith('Min') or dset_name.startswith('Max') else None
            self.query.add_dataset(dset, folder_path=folder_path)

    def read_header(self, file):
        """Reader the header line of an ASCII solution file.

        Args:
            file: Open stream to the file to read
        """
        file.readline()  # skip the first header line - nothing we need
        time_line = file.readline()
        time_line = time_line.split()
        self.num_ts = int(time_line[0])
        self.num_nodes = int(time_line[1])  # number of values can be less if sparse
        # don't care about anything else in the header

    def get_reader(self):
        """Get the appropriate reader method based on filename since ADCIRC uses hard-coded filenames."""
        filename = os.path.basename(self.read_file).lower()
        if 'fort.63.nc' in filename:
            XmLog().instance.info('Reading global elevation NetCDF solution (fort.63.nc)...')
            return self.read_netcdf_elevation
        elif 'fort.64.nc' in filename:
            XmLog().instance.info('Reading global velocity NetCDF solution (fort.64.nc)...')
            return self.read_netcdf_velocity
        elif 'fort.73.nc' in filename:
            XmLog().instance.info('Reading global wind pressure NetCDF solution (fort.73.nc)...')
            return self.read_netcdf_meteor73
        elif 'fort.74.nc' in filename:
            XmLog().instance.info('Reading global wind stress NetCDF solution (fort.74.nc)...')
            return self.read_netcdf_meteor74
        elif 'maxele.63.nc' in filename:
            XmLog().instance.info('Reading global maximum elevation NetCDF solution (maxele.63.nc)...')
            return self.read_netcdf_maxele63
        elif 'maxvel.63.nc' in filename:
            XmLog().instance.info('Reading global maximum velocity NetCDF solution (maxvel.63.nc)...')
            return self.read_netcdf_maxvel63
        elif 'maxwvel.63.nc' in filename:
            XmLog().instance.info('Reading global maximum wind velocity NetCDF solution (maxwvel.63.nc)...')
            return self.read_netcdf_maxwvel63
        elif 'minpr.63.nc' in filename:
            XmLog().instance.info('Reading global minimum wind pressure NetCDF solution (minpr.63.nc)...')
            return self.read_netcdf_minpr63
        elif 'maxrs.63.nc' in filename:
            XmLog().instance.info('Reading global maximum radiation stress NetCDF solution (maxrs.63.nc)...')
            return self.read_netcdf_maxrs63
        elif 'fort.63' in filename:
            XmLog().instance.info('Reading global elevation ASCII solution (fort.63)...')
            return self.read_ascii_elevation
        elif 'fort.64' in filename:
            XmLog().instance.info('Reading global velocity ASCII solution (fort.64)...')
            return self.read_ascii_velocity
        elif 'fort.73' in filename:
            XmLog().instance.info('Reading global wind pressure ASCII solution (fort.73)...')
            return self.read_ascii_meteor73
        elif 'fort.74' in filename:
            XmLog().instance.info('Reading global wind stress ASCII solution (fort.74)...')
            return self.read_ascii_meteor74
        elif 'maxele.63' in filename:
            XmLog().instance.info('Reading global maximum elevation ASCII solution (maxele.63)...')
            return self.read_maxele63
        elif 'maxvel.63' in filename:
            XmLog().instance.info('Reading global maximum velocity ASCII solution (maxvel.63)...')
            return self.read_maxvel63
        elif 'maxwvel.63' in filename:
            XmLog().instance.info('Reading global maximum wind velocity ASCII solution (maxwvel.63)...')
            return self.read_maxwvel63
        elif 'minpr.63' in filename:
            XmLog().instance.info('Reading global minimum wind pressure ASCII solution (minpr.63)...')
            return self.read_minpr63
        elif 'maxrs.63' in filename:
            XmLog().instance.info('Reading global maximum radiation stress ASCII solution (maxrs.63)...')
            return self.read_maxrs63
        elif 'fort.53' in filename:
            XmLog().instance.info('Reading global elevation harmonic analysis ASCII solution (fort.53)...')
            return self.read_ascii_harmonic53
        elif 'fort.54' in filename:
            XmLog().instance.info('Reading global velocity harmonic analysis ASCII solution (fort.54)...')
            return self.read_ascii_harmonic54
        else:  # File doesn't have standard hard-coded filename. Try to figure out what type of file it is.
            XmLog().instance.info('Unable to determine reader from file name. Determining file format from file '
                                  'properties...')
            return self._determine_reader_from_file_properties()

    def _determine_reader_from_file_properties(self):
        """Try to determine a solution file's format from file properties.

        Returns:
            callable: The reader for the solution file's format, or None if not found
        """
        try:  # Try to open the file as a NetCDF file.
            with netCDF4.Dataset(self.read_file, 'r') as f:
                return self._find_netcdf_reader(f)
        except Exception:  # Try to determine the ASCII format.
            return self._find_ascii_reader()

    def _find_netcdf_reader(self, file):
        """Find the appropriate reader for a NetCDF solution file.

        Args:
            file (:obj:`netcdf4.Dataset`): Open handle to the NetCDF file

        Returns:
            callable: The reader for the NetCDF solution file, or None if not found
        """
        if 'zeta' in file.variables:  # fort.63.nc
            return self.read_netcdf_elevation
        elif 'u-vel' in file.variables:  # fort.64.nc
            return self.read_netcdf_velocity
        elif 'pressure' in file.variables:  # fort.73.nc
            return self.read_netcdf_meteor73
        elif 'windx' in file.variables:  # fort.74.nc
            return self.read_netcdf_meteor74
        elif 'zeta_max' in file.variables:  # maxele.63.nc
            return self.read_netcdf_maxele63
        elif 'vel_max' in file.variables:  # maxvel.63.nc
            return self.read_netcdf_maxvel63
        elif 'wind_max' in file.variables:  # maxwvel.63.nc
            return self.read_netcdf_maxwvel63
        elif 'pressure_min' in file.variables:  # minpr.63.nc
            return self.read_netcdf_minpr63
        elif 'radstress_max' in file.variables:  # maxrs.63.nc
            return self.read_netcdf_maxrs63
        return None

    def _find_ascii_reader(self):
        """Find the appropriate reader for an ASCII solution file.

        Returns:
            callable: The reader for the ASCII solution file, or None if not found
        """
        with open(self.read_file, 'r') as f:
            try:
                # If a harmonic analysis solution, second line is: NFREQ
                first_line = f.readline()
                # If a harmonic analysis solution, second line is: HAFREQ(k), HAFF(k), HAFACE(k), NAMEFR(k)
                second_line = f.readline().split()
                num_times = int(second_line[0])
                num_components = int(second_line[4])
                if num_components == 1:
                    if num_times == 2:
                        # If a scalar dataset with two timesteps, most likely a max dataset.
                        return self.read_unknown_ascii_max
                    else:
                        return self.read_unknown_ascii_scalar
                elif num_components == 2:
                    return self.read_unknown_ascii_vector
            except Exception:
                return self._check_for_harmonic_ascii_solution(f, first_line)
        return None

    def _check_for_harmonic_ascii_solution(self, file, first_line):
        """Check if an ASCII file is a harmonic analysis solution.

        Args:
            file: Open stream to the file to read. First two lines should already have been read.
            first_line (:obj:`str`): The first line that was read from the file

        Returns:
            callable: The reader if the file is an ASCII harmonic analysis solution, else None
        """
        try:
            nfreq = int(first_line.split()[0])
            if nfreq > 1:
                for _ in range(nfreq - 1):  # Already read first constituent's properties, skip the rest
                    file.readline()
                file.readline()  # Number of nodes
                file.readline()  # First node's id
                data_line = file.readline().split()
                if len(data_line) == 2:  # If fort.53, line is: EMAGT(k,j), PHASEDE(k,j)
                    return self.read_ascii_harmonic53
                elif len(data_line) == 4:  # If fort.54, line is: UMAGT(k,j), PHASEDU(k,j), VMAGT(k,j), PHASEDV(k,j)
                    return self.read_ascii_harmonic54
        except Exception:
            return None
        return None

    # Readers returned by get_readers()
    def read_ascii_elevation(self):
        """Reader for ASCII elevation solution files (fort.63)."""
        with open(self.read_file, 'r', buffering=IO_BUFFER_SIZE) as f:
            self.read_ascii_scalars(f, 'Water Surface (eta)')

    def read_netcdf_elevation(self):
        """Reader for NetCDF elevation solution files (fort.63.nc)."""
        self.read_netcdf_scalars(self.read_file, '/zeta', 'Water Surface (eta)')

    def read_ascii_velocity(self):
        """Reader for ASCII velocity solution files (fort.64)."""
        with open(self.read_file, 'r', buffering=IO_BUFFER_SIZE) as f:  # fort.64 (velocity) reader
            self.read_ascii_vectors(f, 'Current Velocity (curr)')

    def read_netcdf_velocity(self):
        """Reader for NetCDF velocity solution files (fort.64.nc)."""
        self.read_netcdf_vectors(self.read_file, '/u-vel', '/v-vel', 'Current Velocity (curr)')

    def read_ascii_meteor73(self):
        """Reader for ASCII atmospheric pressure solution files (fort.73)."""
        with open(self.read_file, 'r', buffering=IO_BUFFER_SIZE) as f:
            self.read_ascii_scalars(f, 'Atmospheric Pressure')

    def read_ascii_meteor74(self):
        """Reader for ASCII wind velocity/stress solution files (fort.74)."""
        with open(self.read_file, 'r', buffering=IO_BUFFER_SIZE) as f:
            self.read_ascii_vectors(f, 'Wind Stress')

    def read_netcdf_meteor73(self):
        """Reader for NetCDF atmospheric pressure solution files (fort.73.nc)."""
        self.read_netcdf_scalars(self.read_file, 'pressure', 'Atmospheric Pressure')

    def read_netcdf_meteor74(self):
        """Reader for NetCDF wind velocity/stress solution files (fort.74.nc)."""
        self.read_netcdf_vectors(self.read_file, 'windx', 'windy', 'Wind Stress')

    def read_netcdf_maxele63(self):
        """Reader for NetCDF maximum elevation solution files (maxele.63.nc)."""
        self.read_netcdf_max_scalars(self.read_file, 'zeta_max', 'time_of_zeta_max', 'Max eta')

    def read_netcdf_maxvel63(self):
        """Reader for NetCDF maximum velocity solution files (maxvel.63.nc)."""
        self.read_netcdf_max_scalars(self.read_file, 'vel_max', 'time_of_vel_max', 'Max curr')

    def read_netcdf_maxwvel63(self):
        """Reader for NetCDF maximum wind velocity solution files (maxwvel.63.nc)."""
        self.read_netcdf_max_scalars(self.read_file, 'wind_max', 'time_of_wind_max', 'Max Windvel')

    def read_netcdf_minpr63(self):
        """Reader for NetCDF minimum pressure solution files (minpr.63.nc)."""
        self.read_netcdf_max_scalars(self.read_file, 'pressure_min', 'time_of_pressure_min', 'Min press')

    def read_netcdf_maxrs63(self):
        """Reader for NetCDF maximum wave radiation stress solution files (maxrs.63.nc)."""
        self.read_netcdf_max_scalars(self.read_file, 'radstress_max', 'time_of_radstress_max',
                                     'Max Radstress')

    def read_maxele63(self):
        """Reader for ASCII maximum elevation solution files (maxele.63)."""
        with open(self.read_file, 'r', buffering=IO_BUFFER_SIZE) as f:
            self.read_ascii_max_scalars(f, 'Max eta')

    def read_maxvel63(self):
        """Reader for ASCII maximum velocity solution files (maxvel.63)."""
        with open(self.read_file, 'r', buffering=IO_BUFFER_SIZE) as f:
            self.read_ascii_max_scalars(f, 'Max curr')

    def read_minpr63(self):
        """Reader for ASCII minimum pressure solution files (minpr.63)."""
        with open(self.read_file, 'r', buffering=IO_BUFFER_SIZE) as f:
            self.read_ascii_max_scalars(f, 'Min press')

    def read_maxwvel63(self):
        """Reader for ASCII maximum wind velocity solution files (maxwvel.63)."""
        with open(self.read_file, 'r', buffering=IO_BUFFER_SIZE) as f:
            self.read_ascii_max_scalars(f, 'Max Windvel')

    def read_maxrs63(self):
        """Reader for ASCII maximum wave radiation stress solution files (maxrs.63)."""
        with open(self.read_file, 'r', buffering=IO_BUFFER_SIZE) as f:
            self.read_ascii_max_scalars(f, 'Max Radstress')

    def read_ascii_harmonic53(self):
        """Reader for fort.53 harmonic analysis solution files."""
        with open(self.read_file, 'r', buffering=IO_BUFFER_SIZE) as f:
            self.read_ascii_harmonic(f)

    def read_ascii_harmonic54(self):
        """Reader for fort.54 harmonic analysis solution files."""
        with open(self.read_file, 'r', buffering=IO_BUFFER_SIZE) as f:
            self.read_ascii_harmonic(f, False)

    def read_unknown_ascii_max(self):
        """Reader for ASCII maximum dataset when we aren't sure what the dataset is."""
        with open(self.read_file, 'r', buffering=IO_BUFFER_SIZE) as f:
            self.read_ascii_max_scalars(f, os.path.basename(self.read_file))

    def read_unknown_ascii_scalar(self):
        """Reader for ASCII scalar dataset when we aren't sure what the dataset is."""
        with open(self.read_file, 'r', buffering=IO_BUFFER_SIZE) as f:
            self.read_ascii_scalars(f, os.path.basename(self.read_file))

    def read_unknown_ascii_vector(self):
        """Reader for ASCII scalar dataset when we aren't sure what the dataset is."""
        with open(self.read_file, 'r', buffering=IO_BUFFER_SIZE) as f:
            self.read_ascii_vectors(f, os.path.basename(self.read_file))

    def add_mesh_datasets(self):
        """Read all found solution files."""
        # binary formats not supported (format=2)
        for filename in self.filenames:
            if not os.path.isfile(filename):
                continue
            basename = os.path.basename(filename).lower()
            if basename in NETCDF_STATIONS or basename in ASCII_STATIONS:
                continue  # This is a recording station solution, don't try to read it.
            self.read_file = filename
            reader = self.get_reader()
            if reader:
                reader()
                self.read_data = True
            else:
                XmLog().instance.error(f'Unable to determine format of solution file: {self.read_file}')

    def read(self):
        """Start the solution reader."""
        self.add_mesh_datasets()
        if not self.read_data:
            XmLog().instance.error('No ADCIRC solution files found. Please run the model again.')
