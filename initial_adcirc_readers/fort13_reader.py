"""Reader for ADCIRC fort.13 nodal attribute files."""
# 1. Standard python libraries
import os
import uuid

# 2. Third party libraries
import numpy as np

# 3. Aquaveo libraries
from xms.api.dmi import Query
from xms.api.tree import tree_util
from xms.datasets.dataset_writer import DatasetWriter

# 4. Local libraries
from xms.adcirc.data.sim_data import SimData
from xms.adcirc.feedback.xmlog import XmLog


Z0_LAND_DSET_ATTRS = [  # xarray.Dataset attrs in SimData
    'z0land_000',
    'z0land_030',
    'z0land_060',
    'z0land_090',
    'z0land_120',
    'z0land_150',
    'z0land_180',
    'z0land_210',
    'z0land_240',
    'z0land_270',
    'z0land_300',
    'z0land_330',
]


BRIDGE_PILINGS_DSET_ATTRS = [  # xarray.Dataset attrs in SimData
    'BK',
    'BAlpha',
    'BDelX',
    'POAN',
]


NOLIBF_NODAL_ATT_IDX = {  # Indices of NOLIBF nodal attribute options in SimData
    'quadratic_friction_coefficient_at_sea_floor': 3,
    'mannings_n_at_sea_floor': 4,
    'chezy_friction_coefficient_at_sea_floor': 5,
    'bottom_roughness_length': 6,
}


def get_dset_display_names(a_att, a_units=""):
    """Get the display names of a nodal attribute's datasets from the nodal attribute card.

    This function also sets the cbxNOLIBF text that will be returned to the fort.15 if it triggered this read.

    Args:
        a_att (:obj:`str`): Card value of the nodal attribute from the fort.13 file.
        a_units (:obj:`str`, optional): Physical units of the dataset values. Will be appended to the display name
            if provided.

    Returns:
        (:obj:`list`): List of display names for each dataset of the nodal attribute
    """
    display_names = []
    if a_att == 'surface_submergence_state':
        display_names = ['StartDry']
    elif a_att == 'surface_directional_effective_roughness_length':
        display_names = ['Z0Land000', 'Z0Land030', 'Z0Land060', 'Z0Land090', 'Z0Land120', 'Z0Land150', 'Z0Land180',
                         'Z0Land210', 'Z0Land240', 'Z0Land270', 'Z0Land300', 'Z0Land330']
    elif a_att == 'surface_canopy_coefficient':
        display_names = ['VCanopy']
    elif a_att == 'bottom_roughness_length':  # Can only have one friction nodal attribute
        display_names = ['Z0b_var']
    elif a_att == 'wave_refraction_in_swan':
        display_names = ['SwanWaveRefrac']
    elif a_att == 'average_horizontal_eddy_viscosity_in_sea_water_wrt_depth':
        display_names = ['EVC']
    elif a_att == 'primitive_weighting_in_continuity_equation':
        display_names = ['TAU0']
    elif a_att == 'quadratic_friction_coefficient_at_sea_floor':  # Can only have one friction nodal attribute
        display_names = ['Quadratic friction']
    elif a_att == 'bridge_pilings_friction_paramenters':
        display_names = ['BK', 'BAlpha', 'BDelX', 'POAN']
    elif a_att == 'mannings_n_at_sea_floor':  # Can only have one friction nodal attribute
        display_names = ['ManningsN']
    elif a_att == 'chezy_friction_coefficient_at_sea_floor':  # Can only have one friction nodal attribute
        display_names = ['ChezyFric']
    elif a_att == 'elemental_slope_limiter':
        display_names = ['ElSloLim']
    elif a_att == 'advection_state':
        display_names = ['AdvState']
    elif a_att == 'initial_river_elevation':
        display_names = ['IniRivEle']

    # For now, I am never passing in the units to this function. It is only applicable sometimes, and there are
    # no defined values for the units strings in the fort.13. It can be anything. Currently we do not have a
    # units (other than time units) interface on our data_objects Dataset.
    # add units to the display name if applicable
    if a_units and str(a_units) != "1" and "unitless" not in a_units.lower() and "user" not in a_units.lower():
        for display_name in display_names:
            display_name += f" ({a_units})"

    return display_names


class Fort13Reader:
    """Reads an ADCIRC fort.13 (non-control) file. Nodal attributes (mostly datasets on the mesh)."""
    def __init__(self, filename, query=None, sim_data=None):
        """Initializes the fort.13 reader.

        fort.13 files are not control files, so no new simulation will be created. If a fort.13 is imported as a single
        file, data will be added to the active ADCIRC simulation in SMS. In this case, a mesh must be linked to the
        simulation, and it must have the same number of nodes as number of dataset values in the fort.13.

        Args:
            filename (:obj:`str`): Filename location of the fort.13 to import
            query (:obj:`xms.api.dmi.Query`, optional): Query for communicating with SMS. Must be passed in when called
                from the fort.15.
            sim_data (:obj:`xms.api.dmi.Query`, optional): The simulation component's data. Must be passed in when
                called from the fort.15
        """
        self._filename = filename  # If read triggered by the fort.15, a fort.13 must exist in the same directory.
        self._query = query
        self._sim_data = sim_data
        self._should_send = False if query else True  # Only send data to SMS if the fort.13 is being read individually
        self._num_nodes = 0
        self._num_atts = 0
        self._geom_uuid = ''
        self._att_defaults = {}  # Key=nodal attribute name, value=[default values]
        self._att_dsets = {}  # Key=nodal attribute name, value=[datasets]
        self.built_data = {'nodal_atts': []}
        self.out_filenames = []  # For testing, so we don't have to use Query
        self.dset_uuids = []  # For testing

    def _setup_query(self):  # pragma: no cover
        """Connects a Query to SMS when the fort.13 is being read individually.

        The filename is retrieved from the Query's Session.
        """
        self._query = Query()
        self._filename = self._query.read_file  # If this is an independent read, allow fort.13 file to have any name.

    def _find_sim_data(self):
        """Looks for an appropriate simulation to update given their linked meshes' number of points.

        Priority is given to the active simulation

        Returns:
            (:obj:`bool`): False if connecting to SMS fails.
        """
        XmLog().instance.info('Retrieving simulation data from SMS...')
        # Query for the simulation component's data if this is an independent read.
        try:
            sim_uuid = self._query.current_item_uuid()
            sim_comp = self._query.item_with_uuid(sim_uuid, model_name='ADCIRC', unique_name='Sim_Component')
            if sim_comp and os.path.isfile(sim_comp.main_file):
                # If we have an active sim with a linked mesh and the number of nodes match. Give that mesh priority.
                sim_item = tree_util.find_tree_node_by_uuid(self._query.project_tree, sim_uuid)
                mesh_item = tree_util.descendants_of_type(sim_item, xms_types=['TI_MESH2D_PTR'],
                                                          allow_pointers=True, only_first=True, recurse=False)
                if mesh_item and mesh_item.num_points == self._num_nodes:
                    self._sim_data = SimData(sim_comp.main_file)
                    self._geom_uuid = mesh_item.uuid
                else:  # Look for another sim with a linked mesh that has the correct number
                    mesh_items = tree_util.descendants_of_type(self._query.project_tree, xms_types=['TI_MESH2D_PTR'],
                                                               allow_pointers=True)
                    for mesh_item in mesh_items:
                        parent = mesh_item.parent
                        is_sim = parent.item_typename == 'TI_DYN_SIM' and parent.model_name == 'ADCIRC'
                        if is_sim and mesh_item.num_points == self._num_nodes:
                            sim_comp = self._query.item_with_uuid(parent.uuid, model_name='ADCIRC',
                                                                  unique_name='Sim_Component')
                            if sim_comp and os.path.isfile(sim_comp.main_file):
                                self._sim_data = SimData(sim_comp.main_file)
                                self._geom_uuid = mesh_item.uuid
                                break
        except Exception:
            # We used to require an active simulation with a linked mesh that has the correct number of nodes. We
            # loosened that restriction, so this exception handler should bew unreachable now.
            XmLog().instance.exception('Error retrieving ADCIRC simulation.')
            return False

        return True  # Got everything we need.

    def _get_next_h5_filename_and_uuid(self):
        """Either get a random UUID and filename of an H5 file to write from the Query or hardcoded list if testing.

        Returns:
            (:obj:`tuple (str, str)`): Filesystem path to use to write an H5 file, UUID for the dataset
        """
        if self.out_filenames and self.dset_uuids:
            return self.out_filenames.pop(), self.dset_uuids.pop()
        else:  # pragma: no cover
            dset_uuid = str(uuid.uuid4())
            return os.path.join(self._query.xms_temp_directory, f'{dset_uuid}.h5'), dset_uuid

    def _read_att_info(self, fs):
        """Get the dataset default values for all nodal attributes in the fort.13.

        Args:
            fs: Open file handle to the fort.13 file. The next line in the buffer should be the first line of the first
                nodal attribute's metadata section.
        """
        XmLog().instance.info('Reading nodal attribute properties...')
        for _ in range(self._num_atts):
            att_name = fs.readline().split()[0]
            fs.readline()  # Physical units, don't care
            fs.readline()  # The number of datasets can be implied from the number of defaults on the next line.
            default_vals = [float(val) for val in fs.readline().replace(",", " ").split()]
            self._att_defaults[att_name] = default_vals

    def _read_att_values(self, fs):
        """Get the dataset default values for all nodal attributes in the fort.13.

        Args:
            fs: Open file handle to the fort.13 file. The next line in the buffer should be the first line of the first
                nodal attribute's data section.
        """
        for _ in range(self._num_atts):  # loop through the nodal attributes
            att_name_line = fs.readline().split()
            while not att_name_line:  # Some files in the wild like to put empty lines in between the attribute values
                att_name_line = fs.readline().split()
            att_name = att_name_line[0]
            num_att_dsets = len(self._att_defaults[att_name])
            XmLog().instance.info(
                f'Reading value for nodal attribute: {att_name} '
                f'({num_att_dsets} {"datasets" if num_att_dsets > 1 else "dataset"})'
            )
            num_exceptions = int(fs.readline().split()[0])
            # Initialize arrays to hold the dataset values with defaults previously read from the file.
            dset_vals = [[self._att_defaults[att_name][dset] for _ in range(self._num_nodes)]
                         for dset in range(num_att_dsets)]
            for _ in range(num_exceptions):  # loop through the nodes whose values are not the default
                line_data = fs.readline().replace(",", " ").split()
                node_idx = int(line_data[0]) - 1  # Node id is the first card
                # Loop through the dataset values for this nodal attribute. Data for all datasets at a given node are
                # on a single line.
                for k in range(len(self._att_defaults[att_name])):
                    dset_vals[k][node_idx] = float(line_data[k + 1])

            # Special case for GeiodOffset which is the only attribute that is constant instead of a dataset.
            if att_name == "sea_surface_height_above_geoid":
                if self._sim_data:
                    # Use the mean of the dataset for the edit field if exceptions to the default were specified.
                    # Doesn't make sense but some old files might do it.
                    mean = float(np.array(dset_vals[0]).mean())
                    self._sim_data.nodal_atts.attrs['sea_surface_height_above_geoid_on'] = 1
                    self._sim_data.nodal_atts.attrs['sea_surface_height_above_geoid'] = mean
            else:  # Nodal attributes with one or more datasets
                display_names = get_dset_display_names(att_name)
                if not display_names:
                    # Read the datasets onto the mesh even if we don't know what it is.
                    XmLog().instance.warning(f'Unrecognized nodal attribute found: {att_name}')
                    display_names = [
                        f'{att_name} ({i + 1})' if num_att_dsets != 1 else f'{att_name}' for i in range(num_att_dsets)
                    ]
                for j in range(num_att_dsets):
                    XmLog().instance.info(f'Creating XMDF formatted file for dataset {j + 1} of {num_att_dsets}...')
                    filename, dset_uuid = self._get_next_h5_filename_and_uuid()
                    dset = DatasetWriter(
                        h5_filename=filename,
                        name=display_names[j],
                        dset_uuid=dset_uuid,
                        geom_uuid=self._geom_uuid,
                        location='points'
                    )
                    dset.append_timestep(0.0, dset_vals[j])
                    dset.appending_finished()
                    if att_name not in self._att_dsets:
                        self._att_dsets[att_name] = []
                    self._att_dsets[att_name].append(dset)

    def _update_sim_data_for_att(self, att_name):
        """Update dataset selector references and other widgets in the simulation component's data for an attribute.

        I am only updating Model Control values if this is an independent read. If triggered by fort.15 import, we
        want to let the fort.15 reader handle this. fort.13 may contain datasets that are not used in the simulation.

        Args:
            att_name (:obj:`str`): The ADCIRC nodal attribute name
        """
        XmLog().instance.info(f'Updating simulation parameters for attribute {att_name}...')
        if not self._sim_data or att_name == 'sea_surface_height_above_geoid':
            # GeoidOffset special case has already been handled. If we don't have a sim to update give up as well.
            return
        elif att_name == 'surface_directional_effective_roughness_length':  # Z0land has 12 datasets
            # Only update sim data if independent read, otherwise let fort.15 reader handle
            if self._should_send:  # pragma: no cover
                self._sim_data.nodal_atts.attrs['surface_directional_effective_roughness_length_on'] = 1

            for idx, dset in enumerate(self._att_dsets[att_name]):
                self._sim_data.nodal_atts.attrs[Z0_LAND_DSET_ATTRS[idx]] = dset.uuid
        elif att_name == 'bridge_pilings_friction_paramenters':  # Bridge pilings friction has 4 datasets
            # Only update sim data if independent read, otherwise let fort.15 reader handle
            if self._should_send:  # pragma: no cover
                self._sim_data.nodal_atts.attrs['bridge_pilings_friction_paramenters_on'] = 1

            for idx, dset in enumerate(self._att_dsets[att_name]):
                self._sim_data.nodal_atts.attrs[BRIDGE_PILINGS_DSET_ATTRS[idx]] = dset.uuid
        else:  # All other attributes only have a single dataset
            self._sim_data.nodal_atts.attrs[att_name] = self._att_dsets[att_name][0].uuid

            # Only update sim data if independent read, otherwise let fort.15 reader handle
            if self._should_send:  # pragma: no cover
                if att_name in NOLIBF_NODAL_ATT_IDX:  # Update NOLIBF option if a friction nodal attribute
                    self._sim_data.general.attrs['NOLIBF'] = NOLIBF_NODAL_ATT_IDX[att_name]
                    if att_name == 'bottom_roughness_length':  # Update IM type if Z0b_var nodal attribute is defined.
                        im_type = self._sim_data.formulation.attrs['IM']
                        if im_type in [0, 111112]:  # Z0b_var requires 3D run (0 = 2DDI, 111112 = 2DDI with lumped GWCE)
                            self._sim_data.formulation.attrs['IM'] = 1  # 1 = Barotropic 3D
                elif att_name == 'primitive_weighting_in_continuity_equation':  # TAU0 nodal att enabled in TAU0 option
                    self._sim_data.formulation.attrs['TAU0'] = -3  # -3 = From nodal attribute
                else:  # All other attributes enabled with toggles with naming convention.
                    self._sim_data.nodal_atts.attrs[f'{att_name}_on'] = 1

    def _add_dsets_and_update_sim(self):
        """Adds the previously read in datasets to their proper place in the Context.

        Also sets parent widgets to the proper values as the dataset widgets are dependent on them.
        """
        for att_name, dsets in self._att_dsets.items():  # Loop through the read in nodal attributes
            # Update dataset selector UUIDs in the simulation component data.
            self._update_sim_data_for_att(att_name)
            self.built_data['nodal_atts'].extend(dsets)

    def read(self):
        """Top-level function that starts the read of the fort.13 file."""
        try:
            # If no Query passed in, create one. This is a non-control file read on an existing simulation.
            retrieve_data = False
            if not self._query:  # pragma: no cover
                retrieve_data = True
                self._setup_query()

            if not os.path.isfile(self._filename) or os.path.getsize(self._filename) == 0:
                XmLog().instance.error(f'Error reading fort.13: File not found - {self._filename}')
                return

            with open(self._filename, 'r', buffering=100000) as fs:
                fs.readline()  # First line is grid name - don't care
                self._num_nodes = int(fs.readline().split()[0])  # get the number of nodes
                self._num_atts = int(fs.readline().split()[0])  # get the number of nodal attributes

                # If this is a non-control file look for an appropriate existing simulation to update. Do this after we
                # have read the number of nodes from the file. We will try to find a simulation that has a matching mesh
                # linked and update its attributes, but if there is none we will still try to read just the dataset
                # onto a compatible mesh.
                if retrieve_data:  # pragma: no cover
                    if not self._find_sim_data():
                        return  # Means there was an exception, not that we didn't find a compatible simulation.

                # The fort.13 lists all of the nodal attributes twice. The first pass provides the number of datasets
                # that belong to the attribute and their default values. The second pass is a sparse listing of the
                # dataset values that differ from the default.
                self._read_att_info(fs)
                self._read_att_values(fs)
                self._add_dsets_and_update_sim()

            # Check for invalid fort.13 file that doesn't err out (empty files)
            if self._num_nodes == 0:
                XmLog().instance.error('Invalid fort.13 file.')
            elif self._num_atts == 0:
                XmLog().instance.error(f'"{self._filename}" contains no nodal attributes.')
            else:
                XmLog().instance.info(
                    f'Successfully read ADCIRC nodal attributes from "{self._filename}". Data is ready to send to SMS.'
                )
        except Exception:
            XmLog().instance.exception(
                f'Error occurred while reading ADCIRC nodal attributes from "{self._filename}"'
            )

    def send(self):  # pragma: no cover
        """Send built data back to SMS if this is a independent file import."""
        # Send the data to SMS if this is an independent read.
        if self._should_send:
            if self._sim_data:
                self._sim_data.commit()  # Save updated Model Control values.
            for nodal_att in self.built_data['nodal_atts']:
                # If read is linked to a simulation, will be matched to appropriate mesh by UUID. Otherwise, a
                # matching mesh must exist in SMS.
                self._query.add_dataset(nodal_att)
            self._query.send()
