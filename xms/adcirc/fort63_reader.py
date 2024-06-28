"""Reader for ADCIRC fort.63.nc solution file."""

# 1. Standard python modules
import logging
import os
from typing import Sequence
import uuid

# 2. Third party modules
import netCDF4
import numpy as np

# 3. Aquaveo modules
from xms.datasets.dataset_writer import DatasetWriter

# 4. Local modules


__copyright__ = "(C) Aquaveo 2022"
__license__ = "All rights reserved"

ADCIRC_NULL_VALUE = -99999.0


class Fort63Reader:
    """Reader for ADCIRC fort.63.nc solution file."""

    def __init__(self,
                 file: str,
                 dataset_name: str,
                 geom_uuid: str,
                 geom_num_nodes: int,
                 logger: logging.Logger = None):
        """Construct the "fort.63.nc" reader.

        Args:
            file (:obj:`str`): The file to read.
            dataset_name (:obj:`str`): The dataset name.
            geom_uuid (:obj:`str`): UUID of the associated geometry.
            geom_num_nodes (:obj:`int`): The number of nodes in the geometry.
            logger (:obj:`logging.Logger`, optional): Logger to use. Defaults to None.
        """
        self.file = file
        self.dataset_name = dataset_name
        self.geom_uuid = geom_uuid
        self.geom_num_nodes = geom_num_nodes
        if logger is None:
            self.logger = logging.getLogger(__name__)
        else:
            self.logger = logger
        self.dataset_writer = None
        self.out_filename = None
        self.dset_uuid = str(uuid.uuid4())

    def read(self):
        """Read the file."""
        self._read_netcdf_scalars(self.file, '/zeta', self.dataset_name)

    def _write_xmdf_dataset(self, dset_name: str, times: Sequence[float], data: np.ndarray):
        """Write a solution dataset to an XMDF formatted file that XMS can read.

        Args:
            dset_name (:obj:`str`): Tree item name of the dataset to create in SMS.
            times (:obj:`Sequence`): 1-D array of float time step offsets
            data (:obj:`np.ndarray`): The dataset values organized in XMDF structure. Rows are time steps and columns
                are values.
        """
        if data.size / len(times) != self.geom_num_nodes:
            raise ValueError(f'Incorrect number of values in {dset_name}.')

        self.logger.info(f'Writing the "{dset_name}" dataset values.')
        writer = DatasetWriter(name=dset_name, dset_uuid=self.dset_uuid, geom_uuid=self.geom_uuid,
                               null_value=ADCIRC_NULL_VALUE, time_units='Seconds')
        writer.write_xmdf_dataset(times, data)
        self.dataset_writer = writer

    def _read_netcdf_scalars(self, filename: str, scalar_path: str, dataset_name: str):
        """Read a scalar solution dataset from a NetCDF formatted file.

        Args:
            filename (:obj:`str`): Filesystem path to the NetCDF solution file.
            scalar_path (:obj:`str`): Path in the NetCDF file to the solution dataset
            dataset_name (:obj:`str`): Tree item name of the dataset to create in SMS.
        """
        self.logger.info(f'Reading "{dataset_name}" values from {os.path.basename(filename)}.')
        root_grp = netCDF4.Dataset(filename, "r", format="NETCDF4_CLASSIC")
        scalar_data = root_grp[scalar_path][:]

        # Replace -99999.0 null values with NaN for numpy operations.
        scalar_data[scalar_data == ADCIRC_NULL_VALUE] = np.nan

        # Convert numpy NaNs back to null value for XMDF file.
        scalar_data[np.isnan(scalar_data)] = ADCIRC_NULL_VALUE

        # Write the XMDF file
        self._write_xmdf_dataset(dataset_name, root_grp["/time"][:], scalar_data)
