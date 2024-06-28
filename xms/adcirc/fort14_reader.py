"""Reader for ADCIRC fort.14 geometry files."""

# 1. Standard python modules
import logging
import os
from typing import Optional

# 2. Third party modules

# 3. Aquaveo modules
from xms.constraint import Grid as CoGrid, UGridBuilder
from xms.grid.ugrid import UGrid as XmUGrid

# 4. Local modules


GEOGRAPHIC_WKT = 'GEOGCS["NAD83",DATUM["North_American_Datum_1983",SPHEROID["GRS 1980",6378137,298.257222101,' \
                 'AUTHORITY["EPSG","7019"]],TOWGS84[0,0,0,0,0,0,0],AUTHORITY["EPSG","6269"]],PRIMEM["Greenwich",0,' \
                 'AUTHORITY["EPSG","8901"]],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],' \
                 'AUTHORITY["EPSG","4269"]]'
LOCAL_METERS_WKT = 'LOCAL_CS["None",LOCAL_DATUM["None",0],UNIT["Meter",1],AXIS["None",OTHER]]'


class Fort14Reader:
    """Reads an ADCIRC fort.14 (control) file. Mesh geometry and coverages."""

    def __init__(self, filename: str, logger: Optional[logging.Logger] = None):
        """Initializes the reader.

        Args:
            filename: Full path and filename of the fort.14 file.
            logger: the logger instance.
        """
        self.filename = filename
        if logger is None:
            self.logger = logging.getLogger(__name__)
        else:
            self.logger = logger
        self.mapped_bc_dir = ''
        self.lines = []
        self.mesh_name = ''
        self.pt_map = {}  # {id_in_file: ((x,y,z), point_index)}
        self.assume_geo_coords = False  # If no projection info from fort.15 reader, we will check extents of mesh
        self.num_nodes = 0
        self.num_cells = 0
        self.current_line = 0
        self.wkt = ''
        self.co_grid = None

    def _read_mesh(self):
        """Read the mesh geometry from the fort.14."""
        line_data = self.lines[self.current_line].split()
        self.current_line += 1
        self.num_cells = int(line_data[0])
        self.num_nodes = int(line_data[1])

        # Read the node locations - one per line: point_id pt_x pt_y pt_z
        self.logger.info('Parsing mesh node locations...')
        for _ in range(self.num_nodes):
            line_data = self.lines[self.current_line].split()
            self.current_line += 1
            point_index = len(self.pt_map)
            self.pt_map[int(line_data[0])] = (  # First column is point id
                # Second, third, and fourth columns are the point's x,y,z coordinates. Invert the depth.
                (float(line_data[1]), float(line_data[2]), float(line_data[3]) * -1.0),
                point_index  # Store the point's index in the UGrid point array
            )

        # Read the connectivity - one per line: poly_id num_nodes pt_id (pt1...num_nodes)
        self.logger.info('Parsing mesh element definitions...')
        cell_stream = [stream_val for _ in range(self.num_cells) for stream_val in self._get_cell_stream_vals()]

        # Build the constrained UGrid
        self.logger.info('Building the UGrid...')
        points = [point_data[0] for point_data in self.pt_map.values()]
        u_grid = XmUGrid(points, cell_stream)
        co_builder = UGridBuilder()
        co_builder.set_is_2d()
        co_builder.set_ugrid(u_grid)
        self.co_grid = co_builder.build_grid()
        # Check the extents to see if they are lat,lon if projection not sent from fort.15
        ex_min, ex_max = u_grid.extents
        min_lon, min_lat, _ = ex_min
        max_lon, max_lat, _ = ex_max
        if min_lon >= -180.0 and min_lat >= -90.0 and max_lon <= 180.0 and max_lat <= 90.0:
            self.assume_geo_coords = True

    def _get_cell_stream_vals(self) -> list[int]:
        """Get the XmGrid cell stream definition for the current cell line.

        This method assumes only tri elements are present in the fort.14

        Returns:
            [XmUGrid.cell_type_enum.TRIANGLE, node1_id, node2_id, node3_id]
        """
        line_data = self.lines[self.current_line].split()
        self.current_line += 1
        # Always tri elements
        return [
            XmUGrid.cell_type_enum.TRIANGLE,
            3,
            self.pt_map[int(line_data[2])][1],
            self.pt_map[int(line_data[3])][1],
            self.pt_map[int(line_data[4])][1]
        ]

    def _parse_lines(self):
        """Parse the fort.14."""
        self.logger.info('Loading fort.14 from ASCII file...')
        with open(self.filename, "r") as f:
            self.lines = f.readlines()
        self.mesh_name = self.lines[self.current_line].strip()  # grid name
        self.current_line += 1
        # Read the mesh
        self._read_mesh()
        # Read the boundary conditions and pipes coverages
        # self._read_coverages()

    def _assign_wkt(self):
        """Assign the WKT."""
        if self.assume_geo_coords:
            self.wkt = GEOGRAPHIC_WKT
        else:
            self.wkt = LOCAL_METERS_WKT

    def read(self) -> tuple[Optional[CoGrid], str]:
        """Top-level function that the reads an ADCIRC fort.14 file."""
        if not os.path.isfile(self.filename) or os.path.getsize(self.filename) == 0:
            raise ValueError(f'Error reading fort.14: File not found - {self.filename}')

        # Read the fort.14 and parse the lines
        self._parse_lines()
        self._assign_wkt()
        self.logger.info(f'Successfully read "{self.filename}".')
        return self.co_grid, self.wkt
