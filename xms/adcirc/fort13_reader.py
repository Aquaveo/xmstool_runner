"""Reader for ADCIRC fort.13 nodal attribute files."""
# 1. Standard python libraries
import logging
import os
from typing import Optional
import uuid

# 2. Third party libraries
import numpy as np

# 3. Aquaveo libraries
from xms.datasets.dataset_writer import DatasetWriter

# 4. Local libraries


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


def get_dset_display_names(a_att: str) -> list[str]:
    """Get the display names of a nodal attribute's datasets from the nodal attribute card.

    Args:
        a_att: Card value of the nodal attribute from the "fort.13" file.

    Returns:
        List of display names for each dataset of the nodal attribute
    """
    attribute_map = {
        'surface_submergence_state': ['StartDry'],
        'surface_directional_effective_roughness_length': ['Z0Land000', 'Z0Land030', 'Z0Land060', 'Z0Land090',
                                                           'Z0Land120', 'Z0Land150', 'Z0Land180',
                                                           'Z0Land210', 'Z0Land240', 'Z0Land270', 'Z0Land300',
                                                           'Z0Land330'],
        'surface_canopy_coefficient': ['VCanopy'],
        'bottom_roughness_length': ['Z0b_var'],
        'wave_refraction_in_swan': ['SwanWaveRefrac'],
        'average_horizontal_eddy_viscosity_in_sea_water_wrt_depth': ['EVC'],
        'primitive_weighting_in_continuity_equation': ['TAU0'],
        'quadratic_friction_coefficient_at_sea_floor': ['Quadratic friction'],
        'bridge_pilings_friction_paramenters': ['BK', 'BAlpha', 'BDelX', 'POAN'],
        'mannings_n_at_sea_floor': ['ManningsN'],
        'chezy_friction_coefficient_at_sea_floor': ['ChezyFric'],
        'elemental_slope_limiter': ['ElSloLim'],
        'advection_state': ['AdvState'],
        'initial_river_elevation': ['IniRivEle']
    }

    return attribute_map.get(a_att, [])


class Fort13Reader:
    """Reads an ADCIRC fort.13 (non-control) file and creates datasets containing the nodal attributes."""
    def __init__(self, in_file: str, geom_uuid: str, geom_num_nodes: int, logger: Optional[logging.Logger] = None):
        """Initializes the fort.13 reader.

        The grid must have the same number of points as number of dataset values in the fort.13.

        Args:
            in_file : Filename location of the fort.13 to import.
            geom_uuid : UUID of the geometry.
            geom_num_nodes : Number of grid nodes.
            logger : The logger.
        """
        self._in_file = in_file
        self._geom_uuid = geom_uuid
        self._geom_num_nodes = geom_num_nodes
        if logger is None:
            self._logger = logging.getLogger(__name__)
        else:
            self._logger = logger
        self._num_nodes = 0
        self._num_atts = 0
        self._att_defaults = {}  # Key=nodal attribute name, value=[default values]
        self._att_dsets = {}  # Key=nodal attribute name, value=[datasets]
        self.datasets = {}
        self.built_data = []
        self.nodal_atts = {}
        self.formulation_atts = {}
        self.general_atts = {}

    def _read_att_info(self, fs):
        """Get the dataset default values for all nodal attributes in the fort.13.

        Args:
            fs: Open file handle to the fort.13 file. The next line in the buffer should be the first line of the first
                nodal attribute's metadata section.
        """
        self._logger.info('Reading nodal attribute properties...')
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
            self._logger.info(
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

            # Special case for "GeiodOffset" which is the only attribute that is constant instead of a dataset.
            if att_name == "sea_surface_height_above_geoid":
                # Use the mean of the dataset for the edit field if exceptions to the default were specified.
                # Doesn't make sense but some old files might do it.
                mean = float(np.array(dset_vals[0]).mean())
                self.nodal_atts['sea_surface_height_above_geoid_on'] = 1
                self.nodal_atts['sea_surface_height_above_geoid'] = mean
            else:  # Nodal attributes with one or more datasets
                display_names = get_dset_display_names(att_name)
                if not display_names:
                    # Read the datasets onto the mesh even if we don't know what it is.
                    self._logger.warning(f'Unrecognized nodal attribute found: {att_name}')
                    display_names = [
                        f'{att_name} ({i + 1})' if num_att_dsets != 1 else f'{att_name}' for i in range(num_att_dsets)
                    ]
                for j in range(num_att_dsets):
                    self._logger.info(f'Creating dataset {j + 1} of {num_att_dsets}...')
                    dset_uuid = str(uuid.uuid4())
                    dataset_name = display_names[j]
                    dataset_writer = DatasetWriter(
                        name=dataset_name,
                        dset_uuid=dset_uuid,
                        geom_uuid=self._geom_uuid,
                        location='points'
                    )
                    dataset_writer.append_timestep(0.0, dset_vals[j])
                    dataset_writer.appending_finished()
                    self.datasets[dataset_name] = dataset_writer
                    if att_name not in self._att_dsets:
                        self._att_dsets[att_name] = []
                    self._att_dsets[att_name].append(dataset_writer)

    def _add_dsets_and_update_sim(self):
        """Adds the previously read in datasets to their proper place in the Context."""
        for _, dsets in self._att_dsets.items():
            self.built_data.extend(dsets)

    def read(self):
        """Top-level function that starts the read of the fort.13 file."""
        if not os.path.isfile(self._in_file) or os.path.getsize(self._in_file) == 0:
            raise ValueError(f'Error reading fort.13: File not found - {self._in_file}')

        with open(self._in_file, 'r', buffering=100000) as fs:
            fs.readline()  # First line is grid name - don't care
            self._num_nodes = int(fs.readline().split()[0])  # get the number of nodes
            self._num_atts = int(fs.readline().split()[0])  # get the number of nodal attributes

            # Check for invalid fort.13 file that doesn't err out (empty files)
            if self._num_nodes <= 0:
                raise ValueError('Invalid fort.13 file.')
            elif self._num_nodes != self._geom_num_nodes:
                raise ValueError('Invalid number of nodes.')
            elif self._num_atts == 0:
                raise ValueError(f'"{self._in_file}" contains no nodal attributes.')

            # The fort.13 lists all the nodal attributes twice. The first pass provides the number of datasets
            # that belong to the attribute and their default values. The second pass is a sparse listing of the
            # dataset values that differ from the default.
            self._read_att_info(fs)
            self._read_att_values(fs)
            self._add_dsets_and_update_sim()

        self._logger.info(f'Successfully read ADCIRC nodal attributes from "{self._in_file}".')
