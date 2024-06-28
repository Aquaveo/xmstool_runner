"""Reader for ADCIRC fort.14 geometry files."""
# 1. Standard python modules
import binascii
import os
import uuid

# 2. Third party modules
import numpy as np
import orjson
import xarray as xr

# 3. Aquaveo modules
from xms.api.dmi import Query, XmsEnvironment as XmEnv
from xms.components.display.display_options_io import (read_display_options_from_json,
                                                       write_display_option_line_locations,
                                                       write_display_options_to_json)
from xms.constraint.ugrid_builder import UGridBuilder
from xms.data_objects.parameters import Component, Projection, Simulation, UGrid
from xms.grid.ugrid import UGrid as XmUGrid
from xms.guipy.data.category_display_option_list import CategoryDisplayOptionList
from xms.guipy.data.target_type import TargetType
from xms.guipy.settings import SettingsManager
from xms.guipy.time_format import ISO_DATETIME_FORMAT

# 4. Local modules
from xms.adcirc.components import bc_component_display as bc_disp
from xms.adcirc.data.adcirc_data import UNINITIALIZED_COMP_ID
import xms.adcirc.data.bc_data as bcd
import xms.adcirc.data.mapped_bc_data as mbcd
import xms.adcirc.data.sim_data as smd
from xms.adcirc.feedback.xmlog import XmLog


GEOGRAPHIC_WKT = 'GEOGCS["NAD83",DATUM["North_American_Datum_1983",SPHEROID["GRS 1980",6378137,298.257222101,' \
                 'AUTHORITY["EPSG","7019"]],TOWGS84[0,0,0,0,0,0,0],AUTHORITY["EPSG","6269"]],PRIMEM["Greenwich",0,' \
                 'AUTHORITY["EPSG","8901"]],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],' \
                 'AUTHORITY["EPSG","4269"]]'
LOCAL_METERS_WKT = 'LOCAL_CS["None",LOCAL_DATUM["None",0],UNIT["Meter",1],AXIS["None",OTHER]]'
LOCAL_FEET_WKT = 'LOCAL_CS["None",LOCAL_DATUM["None",0],UNIT["Foot (International)",0.3048],AXIS["None",OTHER]]'


class Fort14Reader:
    """Reads an ADCIRC fort.14 (control) file. Mesh geometry and coverages."""

    def __init__(self, filename, query=None, datafrom15=None):
        """Initializes the reader.

        If the second argument is provided, so must the third. If the second argument is not
        provided, this is assumed to be a fort.14 control file.

        Args:
            filename (:obj:`str`): Full path and filename of the fort.14 file. If query is not provided, this argument
                will be ignored, and the filename will be obtained from the Query.
            query (:obj:`xms.api.dmi.Query`, optional): Query for communicating with SMS. If none provided, the
                fort.14 will be considered a control file and a new simulation will be created.
            datafrom15 (:obj:`DataForThe14`, optional): Contains cross file dependency data when reading a fort.14
                as part of a fort.15 import.
        """
        self.filename = filename
        self.mapped_bc_dir = ''
        self.constraint_file = os.path.join(XmEnv.xms_environ_process_temp_directory(), str(uuid.uuid4()))
        self.lines = []
        self.query = query
        self.is_control = True if not query else False
        self.mesh_name = ''
        self.mesh_uuid = datafrom15.mesh_uuid if datafrom15 else str(uuid.uuid4())
        # self.is_control = False  # uncomment this line to debug boundary condition read when fort.14 is a control file
        self.pt_map = {}  # {id_in_file: ((x,y,z), point_index)}
        self.pipes = []  # list of lists - Inner list: [0]=location [1]=height, [2]=coefficient, [3]=diameter
        self.datafrom15 = datafrom15
        self.assume_geo_coords = False  # If no projection info from fort.15 reader, we will check extents of mesh
        self.numnodes = 0
        self.numcells = 0
        self.current_line = 0
        self.ocean_boundaries = []
        self.river_boundaries = []
        self.mapped_data = None
        self.proj = None
        self.wkt = ''
        self.built_data = {}
        self.new_simulation = None  # Will be (Simulation, Component) if control file read

    def _populate_bc_atts(self, ib_type, comp_id):
        """Populate a BC nodestring's atts based on the IBTYPE in the fort.15.

        Args:
            ib_type (:obj:`int`): The BC nodestring's IBTYPE as it appears in the fort.14
            comp_id (:obj:`int`): The component id of the arc to populate atts for
        """
        if ib_type % 10 == 0 and ib_type < 30:  # Mainland types
            self.mapped_data.source_data.arcs['type'].loc[dict(comp_id=[comp_id])] = bcd.MAINLAND_INDEX
            if ib_type == 20:
                self.mapped_data.source_data.arcs['bc_option'].loc[dict(comp_id=[comp_id])] = bcd.NATURAL_INDEX
            else:
                self.mapped_data.source_data.arcs['bc_option'].loc[dict(comp_id=[comp_id])] = bcd.ESSENTIAL_INDEX
                if ib_type == 0:
                    self.mapped_data.source_data.arcs['tang_slip'].loc[dict(comp_id=[comp_id])] = 1
        elif ib_type % 10 == 1 and ib_type < 30:  # Island types
            self.mapped_data.source_data.arcs['type'].loc[dict(comp_id=[comp_id])] = bcd.ISLAND_INDEX
            if ib_type == 21:
                self.mapped_data.source_data.arcs['bc_option'].loc[dict(comp_id=[comp_id])] = bcd.NATURAL_INDEX
            else:
                self.mapped_data.source_data.arcs['bc_option'].loc[dict(comp_id=[comp_id])] = bcd.ESSENTIAL_INDEX
                if ib_type == 1:
                    self.mapped_data.source_data.arcs['tang_slip'].loc[dict(comp_id=[comp_id])] = 1
        elif ib_type % 10 == 2 and ib_type < 30:  # River inflow types
            self.mapped_data.source_data.arcs['type'].loc[dict(comp_id=[comp_id])] = bcd.RIVER_INDEX
            if ib_type == 22:
                self.mapped_data.source_data.arcs['bc_option'].loc[dict(comp_id=[comp_id])] = bcd.NATURAL_INDEX
            else:
                self.mapped_data.source_data.arcs['bc_option'].loc[dict(comp_id=[comp_id])] = bcd.ESSENTIAL_INDEX
                if ib_type == 2:
                    self.mapped_data.source_data.arcs['tang_slip'].loc[dict(comp_id=[comp_id])] = 1
        elif ib_type % 10 == 3:  # Levee outflow types
            self.mapped_data.source_data.arcs['type'].loc[dict(comp_id=[comp_id])] = bcd.LEVEE_OUTFLOW_INDEX
            if ib_type == 23:
                self.mapped_data.source_data.arcs['bc_option'].loc[dict(comp_id=[comp_id])] = bcd.NATURAL_INDEX
            else:
                self.mapped_data.source_data.arcs['bc_option'].loc[dict(comp_id=[comp_id])] = bcd.ESSENTIAL_INDEX
                if ib_type == 3:
                    self.mapped_data.source_data.arcs['tang_slip'].loc[dict(comp_id=[comp_id])] = 1
        elif ib_type % 10 == 4 or ib_type % 10 == 5:  # Levee types
            self.mapped_data.source_data.arcs['type'].loc[dict(comp_id=[comp_id])] = bcd.LEVEE_INDEX
        elif ib_type in [30, 32]:  # Radiation types
            # We do not currently support IBTYPE=32 (Radiation with flux)
            self.mapped_data.source_data.arcs['type'].loc[dict(comp_id=[comp_id])] = bcd.RADIATION_INDEX
        elif ib_type in [40, 41]:  # Zero normal types
            self.mapped_data.source_data.arcs['type'].loc[dict(comp_id=[comp_id])] = bcd.ZERO_NORMAL_INDEX
            if ib_type == 41:
                self.mapped_data.source_data.arcs['galerkin'].loc[dict(comp_id=[comp_id])] = 1
        elif ib_type == 52:  # Flow and radiation types
            self.mapped_data.source_data.arcs['type'].loc[dict(comp_id=[comp_id])] = bcd.FLOW_AND_RADIATION_INDEX

    def _setup_query(self):  # pragma: no cover
        """Connects a Query to SMS when the fort.14 is being read as a control file.

        The filename is retrieved from the Query Session, but it is currently always "fort.14" in the cwd.

        Returns:
            (:obj:`bool`): False if connecting to SMS fails.
        """
        self.query = Query()
        self.filename = self.query.read_file

        # Get the XMS temp directory
        comp_dir = os.path.join(self.query.xms_temp_directory, 'Components')
        self.mapped_bc_dir = os.path.join(comp_dir, str(uuid.uuid4()))
        os.makedirs(self.mapped_bc_dir, exist_ok=True)

    def _read_mesh(self):
        """Read the mesh geometry from the fort.14."""
        line_data = self.lines[self.current_line].split()
        self.current_line += 1
        self.numcells = int(line_data[0])
        self.numnodes = int(line_data[1])

        # Read the node locations - one per line: point_id pt_x pt_y pt_z
        XmLog().instance.info('Parsing mesh node locations...')
        for _ in range(self.numnodes):
            line_data = self.lines[self.current_line].split()
            self.current_line += 1
            point_index = len(self.pt_map)
            self.pt_map[int(line_data[0])] = (  # First column is point id
                # Second, third, and fourth columns are the point's x,y,z coordinates. Invert the depth.
                (float(line_data[1]), float(line_data[2]), float(line_data[3]) * -1.0),
                point_index  # Store the point's index in the UGrid point array
            )

        # Read the connectivity - one per line: poly_id num_nodes pt_id (pt1...num_nodes)
        XmLog().instance.info('Parsing mesh element definitions...')
        cellstream = [stream_val for _ in range(self.numcells) for stream_val in self._get_cellstream_vals()]

        # Build the constrained UGrid
        XmLog().instance.info('Writing mesh to .xmc format...')
        points = [point_data[0] for point_data in self.pt_map.values()]
        xmugrid = XmUGrid(points, cellstream)
        co_builder = UGridBuilder()
        co_builder.set_is_2d()
        co_builder.set_ugrid(xmugrid)
        cogrid = co_builder.build_grid()
        # Set the UUID on the CoGrid as well as the data_objects UGrid so they match when checking for an out-of-date
        # mesh.
        cogrid.uuid = self.mesh_uuid
        cogrid.write_to_file(self.constraint_file, True)
        if not self.datafrom15:  # Check the extents to see if they are lat,lon if projection not sent from fort.15
            ex_min, ex_max = xmugrid.extents
            min_lon, min_lat, _ = ex_min
            max_lon, max_lat, _ = ex_max
            if min_lon >= -180.0 and min_lat >= -90.0 and max_lon <= 180.0 and max_lat <= 90.0:
                self.assume_geo_coords = True

    def _get_cellstream_vals(self):
        """Get the XmGrid cellstream definition for the current cell line.

        This method assumes only tri elements are present in the fort.14

        Returns:
            (:obj:`list`): [XmUGrid.cell_type_enum.TRIANGLE, node1_id, node2_id, node3_id]
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

    def _read_coverages(self):
        """Read the coverage definitions from the fort.14."""
        XmLog().instance.info('Parsing boundary conditions data...')
        self.mapped_data = mbcd.MappedBcData(os.path.join(self.mapped_bc_dir, mbcd.MAPPED_BC_MAIN_FILE))

        # Limited support for non-periodic water level forcing, keep a file reference if one exists
        fort19 = os.path.join(os.path.dirname(self.filename), 'fort.19')
        if os.path.isfile(fort19):
            self.mapped_data.source_data.info.attrs['periodic_tidal'] = 0
            self.mapped_data.source_data.info.attrs['fort.19'] = os.path.normpath(fort19)

        # Limited support for non-periodic flow forcing, keep a file reference
        fort20 = os.path.join(os.path.dirname(self.filename), 'fort.20')
        if os.path.isfile(fort20):
            self.mapped_data.source_data.info.attrs['periodic_flow'] = 0
            self.mapped_data.source_data.info.attrs['fort.20'] = os.path.normpath(fort20)

        # Datasets we will be building up
        comp_id_data = []
        partner_id_data = []
        nodes_start_idx_data = []
        node_count_data = []
        levee_data = {
            'node1': [],
            'node2': [],
            'height': [],
            'sub_coef': [],
            'super_coef': [],
            'pipe_on': [],
            'pipe_z': [],
            'pipe_diameter': [],
            'pipe_coef': [],
        }
        nodes = []
        levee_coords = []
        # Nodestring locations for the mapped BC component display
        snap_locations = [[], [], [], [], [], [], [], [], [], [], []]
        # Read the number of ocean arcs
        if self.current_line < len(self.lines):
            line_data = self.lines[self.current_line].split()
            self.current_line += 2  # Next line is total number of ocean nodes - don't care
            num_ocean_arcs = int(line_data[0]) if line_data else 0
            XmLog().instance.info('Processing ocean boundaries...')
            for _ in range(num_ocean_arcs):
                # Read the number of nodes for this arc
                line_data = self.lines[self.current_line].split()
                self.current_line += 1
                num_arc_nodes = int(line_data[0])

                # Create a new dataset for the nodestring
                comp_id = self.mapped_data.source_data.add_bc_atts()
                self.mapped_data.source_data.arcs['type'].loc[dict(comp_id=[comp_id])] = bcd.OCEAN_INDEX
                comp_id_data.append(comp_id)
                partner_id_data.append(UNINITIALIZED_COMP_ID)
                nodes_start_idx_data.append(len(nodes))
                node_count_data.append(num_arc_nodes)

                nodestring_locs = []
                for _ in range(num_arc_nodes):
                    line_data = self.lines[self.current_line].split()
                    self.current_line += 1
                    pt_id = int(line_data[0])
                    pt_data = self.pt_map[pt_id]
                    nodestring_locs.extend(pt_data[0])
                    nodes.append(pt_data[1] + 1)
                snap_locations[bcd.OCEAN_INDEX].append(nodestring_locs)
            self.ocean_boundaries.extend(nodes)

        # Read the number of land arcs
        XmLog().instance.info('Processing land boundaries...')
        line = ''
        num_lines = len(self.lines)
        if self.current_line < num_lines:
            line = self.lines[self.current_line]
            self.current_line += 2  # Next line is total number of land nodes - don't care
        num_land_arcs = 0
        if line:
            line_data = line.split()
            num_land_arcs = int(line_data[0])
        read_next_line = True
        line = ""
        for _ in range(num_land_arcs):
            if self.current_line >= num_lines:
                read_next_line = False
                break
            # Read the number of nodes for this arc
            line = self.lines[self.current_line]
            self.current_line += 1
            if not line:  # unexpected end of land arcs
                read_next_line = False
                break
            try:
                line_data = line.split()
                num_arc_nodes = int(line_data[0])
                ib_type = int(line_data[1])
            except ValueError:  # unexpected end of arcs
                read_next_line = False
                break

            # Create a new dataset for the nodestring
            comp_id = self.mapped_data.source_data.add_bc_atts()
            self._populate_bc_atts(ib_type, comp_id)
            comp_id_data.append(comp_id)
            node_count_data.append(num_arc_nodes)
            nodes_start_idx_data.append(len(nodes))
            if ib_type % 10 == 3:  # read levee outflow table
                partner_id_data.append(UNINITIALIZED_COMP_ID)
                levee_coords.extend([comp_id for _ in range(num_arc_nodes)])
                self._read_levee_outflow(num_arc_nodes, levee_data, nodes, snap_locations)
            elif ib_type % 10 == 4 or ib_type % 10 == 5:  # read levee sets and pipe data
                # If this is a levee pair, add two nodestrings to the dataset
                comp_id_data.append(comp_id)
                node_count_data.append(num_arc_nodes)
                nodes_start_idx_data.append(len(nodes) + num_arc_nodes)
                levee_coords.extend([comp_id for _ in range(num_arc_nodes)])
                nodestring1_idx = len(partner_id_data)
                nodestring2_idx = len(partner_id_data) + 1
                partner_id_data.extend([nodestring2_idx, nodestring1_idx])
                self._read_levee_and_pipe(num_arc_nodes, levee_data, nodes, snap_locations)
            else:  # "Simple" land boundary arc types
                partner_id_data.append(UNINITIALIZED_COMP_ID)
                nodestring_locs = []
                bc_type = int(self.mapped_data.source_data.arcs['type'].loc[dict(comp_id=[comp_id])].item())
                for _ in range(num_arc_nodes):
                    line_data = self.lines[self.current_line].split()
                    self.current_line += 1
                    pt_id = int(line_data[0])
                    pt_data = self.pt_map[pt_id]
                    nodestring_locs.extend(pt_data[0])
                    nodes.append(pt_data[1] + 1)
                    if bc_type == bcd.RIVER_INDEX:
                        self.river_boundaries.append(nodes[-1])
                snap_locations[bc_type].append(nodestring_locs)

        # Read the number of generic arcs
        if read_next_line and self.current_line < len(self.lines):  # Still more to read
            line = self.lines[self.current_line]
            self.current_line += 1
        num_generic_arcs = 0
        line_data = line.split()
        if line_data:
            num_generic_arcs = int(line_data[0])
        self.current_line += 1  # Next line is total number of generic nodes - don't care
        for _ in range(num_generic_arcs):
            if self.current_line >= num_lines:
                break
            # Read the number of nodes for this arc
            line = self.lines[self.current_line]
            self.current_line += 1
            if not line:  # unexpected end of generic arcs
                break
            line_data = line.split()
            num_arc_nodes = int(line_data[0])

            # Create a new dataset for the nodestring
            comp_id = self.mapped_data.source_data.add_bc_atts()
            comp_id_data.append(comp_id)
            partner_id_data.append(UNINITIALIZED_COMP_ID)
            nodes_start_idx_data.append(len(nodes))
            node_count_data.append(num_arc_nodes)

            nodestring_locs = []
            for _ in range(num_arc_nodes):
                line_data = self.lines[self.current_line].split()
                self.current_line += 1
                pt_id = int(line_data[0])
                pt_data = self.pt_map[pt_id]
                nodestring_locs.extend(pt_data[0])
                nodes.append(pt_data[1] + 1)
            snap_locations[bcd.UNASSIGNED_INDEX].append(nodestring_locs)

        # Flush the imported data to component main file.
        XmLog().instance.info('Writing processed boundary conditions data to disk...')
        self.mapped_data.source_data.commit()
        data_dict = {
            'comp_id': xr.DataArray(data=np.array(comp_id_data, dtype=np.int32)),
            'partner_id': xr.DataArray(data=np.array(partner_id_data, dtype=np.int32)),
            'nodes_start_idx': xr.DataArray(data=np.array(nodes_start_idx_data, dtype=np.int32)),
            'node_count': xr.DataArray(data=np.array(node_count_data, dtype=np.int32)),
        }
        self.mapped_data.nodestrings = xr.Dataset(data_vars=data_dict)
        node_dict = {
            'id': xr.DataArray(data=np.array(nodes, dtype=np.int32))
        }
        self.mapped_data.nodes = xr.Dataset(data_vars=node_dict)
        levee_dict = {
            'Node1 Id': ('comp_id', np.array(levee_data['node1'], dtype=np.int32)),
            'Node2 Id': ('comp_id', np.array(levee_data['node2'], dtype=np.int32)),
            'Zcrest (m)': ('comp_id', np.array(levee_data['height'], dtype=np.float64)),
            'Subcritical __new_line__ Flow Coef': ('comp_id', np.array(levee_data['sub_coef'], dtype=np.float64)),
            'Supercritical __new_line__ Flow Coef': ('comp_id', np.array(levee_data['super_coef'], dtype=np.float64)),
            'Pipe': ('comp_id', np.array(levee_data['pipe_on'], dtype=np.int32)),
            'Zpipe (m)': ('comp_id', np.array(levee_data['pipe_z'], dtype=np.float64)),
            'Pipe __new_line__ Diameter (m)': ('comp_id', np.array(levee_data['pipe_diameter'], dtype=np.float64)),
            'Bulk __new_line__ Coefficient': ('comp_id', np.array(levee_data['pipe_coef'], dtype=np.float64)),
        }
        coords = {'comp_id': levee_coords}
        self.mapped_data.levees = xr.Dataset(data_vars=levee_dict, coords=coords)

        # Save CRC of the grid file for future reference. If user edits the mesh, this mapping is invalid.
        with open(self.constraint_file, 'rb') as f:
            self.mapped_data.info.attrs['grid_crc'] = str(hex(binascii.crc32(f.read()) & 0xFFFFFFFF))

        self._write_location_display_files(snap_locations)

    def _write_location_display_files(self, snap_locations):
        """Write the line location display files.

        Args:
            snap_locations (:obj:`list`): 2D list with inner list for each of the BC types that contains the line x,y,z
                definitions
        """
        # Write the arc location files for component display.
        for bc_type in range(bcd.FLOW_AND_RADIATION_INDEX + 1):  # These are the regular source BC types
            if snap_locations[bc_type]:
                loc_file = bc_disp.BcComponentDisplay.get_display_id_file(bc_type, self.mapped_bc_dir)
                write_display_option_line_locations(loc_file, snap_locations[bc_type])
        # Last category is pipes. In source coverage a pipe is represented with a coverage point between two levee
        # arcs. In the mapped object, we draw a line between the two pipe nodes.
        if snap_locations[-1]:
            loc_file = os.path.join(self.mapped_bc_dir, bc_disp.BC_POINT_ID_FILE)
            write_display_option_line_locations(loc_file, snap_locations[-1])

    def _read_levee_outflow(self, num_nodes, levee_data, nodes, snap_locations):
        """Reads levee outflow boundary arc parameters.

        Args:
            num_nodes (:obj:`int`): The number of nodes in the nodestring.
            levee_data (:obj:`dict`): Data dictionary for the levee dataset. Will be appended to.
            nodes (:obj:`list`): The nodestring nodes list. Will be appended to.
            snap_locations (:obj:`list`): The nodestring locations list for display. Will be appended to.
        """
        # Read the data from the file
        heights = [0.0 for _ in range(num_nodes)]
        flow_coefs = [0.0 for _ in range(num_nodes)]
        node_ids = [-1 for _ in range(num_nodes)]
        nodestring_locs = []
        for i in range(num_nodes):
            line_data = self.lines[self.current_line].split()
            self.current_line += 1
            pt_id = int(line_data[0])
            pt_data = self.pt_map[pt_id]
            node_ids[i] = pt_data[1] + 1
            heights[i] = float(line_data[1])
            flow_coefs[i] = float(line_data[2])
            nodestring_locs.extend(pt_data[0])
        nodes.extend(node_ids)
        snap_locations[bcd.LEVEE_OUTFLOW_INDEX].append(nodestring_locs)

        levee_data['node1'].extend(node_ids)
        levee_data['node2'].extend([UNINITIALIZED_COMP_ID for _ in range(num_nodes)])
        levee_data['height'].extend(heights)
        levee_data['sub_coef'].extend([0.0 for _ in range(num_nodes)])
        levee_data['super_coef'].extend(flow_coefs)
        levee_data['pipe_on'].extend([0 for _ in range(num_nodes)])
        levee_data['pipe_z'].extend([0.0 for _ in range(num_nodes)])
        levee_data['pipe_diameter'].extend([0.0 for _ in range(num_nodes)])
        levee_data['pipe_coef'].extend([0.0 for _ in range(num_nodes)])

    def _read_levee_and_pipe(self, num_nodes, levee_data, nodes, snap_locations):
        """Reads levee pair boundary arc and pipe point parameters.

        Args:
            num_nodes (:obj:`int`): The number of nodes in the nodestring.
            levee_data (:obj:`dict`): Data dictionary for the levee dataset. Will be appended to.
            nodes (:obj:`list`): The nodestring nodes list. Will be appended to.
            snap_locations (:obj:`list`): The nodestring locations list for display. Will be appended to.
        """
        # Read the data from the file
        node1_ids = [-1 for _ in range(num_nodes)]
        node2_ids = [-1 for _ in range(num_nodes)]
        heights = [0.0 for _ in range(num_nodes)]
        sub_flow_coefs = [0.0 for _ in range(num_nodes)]
        super_flow_coefs = [0.0 for _ in range(num_nodes)]
        pipe_ons = [0 for _ in range(num_nodes)]
        pipe_zs = [0.0 for _ in range(num_nodes)]
        pipe_diameters = [0.0 for _ in range(num_nodes)]
        pipe_coeffs = [0.0 for _ in range(num_nodes)]
        nodestring1_locs = []
        nodestring2_locs = []
        for i in range(num_nodes):
            line_data = self.lines[self.current_line].partition('!')[0].split()
            self.current_line += 1
            pt1_id = int(line_data[0])
            pt2_id = int(line_data[1])
            pt1_data = self.pt_map[pt1_id]
            pt2_data = self.pt_map[pt2_id]
            node1_ids[i] = pt1_data[1] + 1
            node2_ids[i] = pt2_data[1] + 1
            heights[i] = float(line_data[2])
            sub_flow_coefs[i] = float(line_data[3])
            super_flow_coefs[i] = float(line_data[4])

            pt1_loc = pt1_data[0]
            pt2_loc = pt2_data[0]
            nodestring1_locs.extend(pt1_loc)
            nodestring2_locs.extend(pt2_loc)
            if len(line_data) > 7:  # read the pipe data if it exists
                height = float(line_data[5])
                pipe_zs[i] = height
                if height < 100.0:  # 100.0 is the null value for pipes
                    pipe_ons[i] = 1
                    # Add a line between the two pipe nodes if the pipe is enabled.
                    pipe_locs = list(pt1_loc)
                    pipe_locs.extend(pt2_loc)
                    snap_locations[bcd.FLOW_AND_RADIATION_INDEX + 1].append(pipe_locs)
                pipe_coeffs[i] = float(line_data[6])
                pipe_diameters[i] = float(line_data[7])

        nodes.extend(node1_ids)
        nodes.extend(node2_ids)
        snap_locations[bcd.LEVEE_INDEX].append(nodestring1_locs)
        snap_locations[bcd.LEVEE_INDEX].append(nodestring2_locs)
        levee_data['node1'].extend(node1_ids)
        levee_data['node2'].extend(node2_ids)
        levee_data['height'].extend(heights)
        levee_data['sub_coef'].extend(sub_flow_coefs)
        levee_data['super_coef'].extend(super_flow_coefs)
        levee_data['pipe_on'].extend(pipe_ons)
        levee_data['pipe_z'].extend(pipe_zs)
        levee_data['pipe_diameter'].extend(pipe_diameters)
        levee_data['pipe_coef'].extend(pipe_coeffs)

    def _build_mesh(self):
        """Builds the data_objects Mesh from the geometric data previously read in."""
        # Build the mesh
        mesh = UGrid(self.constraint_file, name=self.mesh_name)
        # Set the UUID on the CoGrid as well as the data_objects UGrid so they match when checking for an out-of-date
        # mesh.
        mesh.uuid = self.mesh_uuid
        self.wkt = ''
        if self.datafrom15:
            if self.datafrom15.geo_coords:
                self.wkt = GEOGRAPHIC_WKT
            else:
                if self.datafrom15.vert_units == 'METERS':
                    self.wkt = LOCAL_METERS_WKT
                else:
                    self.wkt = LOCAL_FEET_WKT
        else:
            # If reading a fort.14 individually, assume Meter vertical units and check extents of the domain
            # to see if they are valid lat, lon coords.
            if self.assume_geo_coords:
                self.wkt = GEOGRAPHIC_WKT
            else:
                self.wkt = LOCAL_METERS_WKT

        self.proj = Projection(wkt=self.wkt)
        mesh.projection = self.proj

        # add the mesh to the Query Context
        self.built_data['domain_mesh'] = mesh

    def _build_mapped_bc_component(self):
        """Builds the mapped BC component."""
        self._write_mapped_bc_display_options()
        self.mapped_data.info.attrs['wkt'] = self.wkt
        self.mapped_data.commit()

        comp = Component(
            name='Boundary Conditions (applied)',
            comp_uuid=os.path.basename(self.mapped_bc_dir),
            main_file=os.path.join(self.mapped_bc_dir, mbcd.MAPPED_BC_MAIN_FILE),
            model_name='ADCIRC',
            unique_name='Mapped_Bc_Component',
            locked=False
        )
        self.built_data['mapped_bc'] = comp

    def _build_default_sim(self):
        """Creates a simulation with default data when being read as a control file.

        Returns:
            (:obj:`tuple(Simulation, Component)`): The simulation data_object and its hidden component data_object
        """
        # Add a simulation with default values since we are being read independently.
        sim = Simulation(name='Sim', model='ADCIRC', sim_uuid=str(uuid.uuid4()))

        # Create the simulation's hidden component data
        comp_uuid = str(uuid.uuid4())
        sim_comp_dir = os.path.join(os.path.dirname(self.mapped_bc_dir), comp_uuid)
        os.makedirs(sim_comp_dir, exist_ok=True)
        sim_mainfile = os.path.join(sim_comp_dir, smd.SIM_COMP_MAIN_FILE)
        sim_data = smd.SimData(sim_mainfile)  # This will create a default model control

        # Initialize the simulation reference date to the current SMS global zero time.
        sim_data.timing.attrs['ref_date'] = self.query.global_time.strftime(ISO_DATETIME_FORMAT)
        sim_data.commit()

        # Create a data_object for the simulation's hidden component
        comp = Component(comp_uuid=comp_uuid, main_file=sim_mainfile, model_name='ADCIRC', unique_name='Sim_Component',
                         locked=False)
        return sim, comp

    def _write_mapped_bc_display_options(self):
        """Write display options json file for the mapped BC component.

        Set projection info to match the ADCIRC mesh.
        """
        settings = SettingsManager()
        json_text = settings.get_setting('xmsadcirc', bc_disp.REG_KEY_MAPPED_BC_ARC)
        from_registry = False
        if json_text:  # Try reading from the registry first.
            json_dict = orjson.loads(json_text)
            from_registry = True
        else:
            # Copy over some default arc display options for the mapped BC component
            default_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'gui', 'resources', 'default_data',
                                        bc_disp.DEFAULT_BC_JSON)
            json_dict = read_display_options_from_json(default_file)

        categories = CategoryDisplayOptionList()  # Generates a random UUID key for the display list
        categories.from_dict(json_dict)
        categories.is_ids = False
        categories.target_type = TargetType.arc
        categories.comp_uuid = os.path.basename(self.mapped_bc_dir)
        categories.projection = {'wkt': self.wkt}

        # Append the pipe category to the list, but only if we didn't read it from the registry. We draw pipes as
        # lines in the mapped component display.
        if not from_registry:
            pipe_category = bc_disp.BcComponentDisplay.default_pipe_line_atts(categories.categories[-1].id + 1)
            categories.categories.append(pipe_category)

        write_display_options_to_json(os.path.join(self.mapped_bc_dir, bc_disp.BC_JSON), categories)
        self.mapped_data.info.attrs['display_uuid'] = categories.uuid

    def _parse_lines(self):
        XmLog().instance.info('Loading fort.14 from ASCII file...')
        with open(self.filename, "r") as f:
            self.lines = f.readlines()
        self.mesh_name = self.lines[self.current_line].strip()  # grid name
        self.current_line += 1
        if self.datafrom15 and self.datafrom15.mesh_name:
            self.mesh_name = self.datafrom15.mesh_name
        # Read the mesh
        self._read_mesh()
        # Read the boundary conditions and pipes coverages
        self._read_coverages()

    def read(self):
        """Top-level function that starts the read of the fort.14 file."""
        # If no Query passed in, create one. This is a control file read.
        try:
            if not self.query:  # pragma: no cover
                self._setup_query()
            else:  # If called from a fort.15 import, create the mapped BC component folder
                self.mapped_bc_dir = os.path.join(self.datafrom15.comp_dir, str(uuid.uuid4()))
                os.makedirs(self.mapped_bc_dir, exist_ok=True)

            if not os.path.isfile(self.filename) or os.path.getsize(self.filename) == 0:
                XmLog().instance.error(f'Error reading fort.14: File not found - {self.filename}')
                return

            # Read the fort.14 and parse the lines
            self._parse_lines()

            # Build the data_objects to send back to SMS.
            XmLog().instance.info('Creating data objects to send to SMS...')
            self._build_mesh()
            self._build_mapped_bc_component()
            # If running a recording test, only print the basename.
            filename = os.path.basename(self.filename) if XmEnv.xms_environ_running_tests() == 'TRUE' else self.filename
            XmLog().instance.info(f'Successfully read "{filename}". Data is ready to send to SMS.')
        except Exception:
            XmLog().instance.exception(f'Error reading fort.14: {self.filename}')

    def send(self):  # pragma: no cover
        """Send built data to XMS."""
        XmLog().instance.info('Sending imported data to XMS...')
        if self.is_control:
            sim, sim_comp = self._build_default_sim()
            self.query.add_simulation(sim, [sim_comp])

            if 'domain_mesh' in self.built_data:
                self.query.add_ugrid(self.built_data['domain_mesh'])
                self.query.link_item(sim.uuid, self.built_data['domain_mesh'].uuid)
            if 'mapped_bc' in self.built_data:
                self.query.add_component(self.built_data['mapped_bc'])
                self.query.link_item(sim.uuid, self.built_data['mapped_bc'].uuid)

            self.query.send()
