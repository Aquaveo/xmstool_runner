"""Resource utility methods for xmsguipy."""
# 1. Standard python modules
import os

# 2. Third party modules

# 3. Aquaveo modules

# 4. Local modules

__copyright__ = "(C) Copyright Aquaveo 2019"
__license__ = "All rights reserved"

XMS_TYPE_TO_ICON = {
    'TI_CGRID2D': ':/resources/icons/2d_cartesian_grid.svg',
    'TI_COMPONENT': ':/resources/icons/component.svg',
    'TI_COVER': ':/resources/icons/coverage_active.svg',
    'TI_DYN_SIM': ':/resources/icons/simulation.svg',
    'TI_DYN_SIM_FOLDER': ':/resources/icons/simulation_data.svg',
    'TI_FOLDER': ':/resources/icons/folder.svg',
    'TI_GENERIC_ARC': ':/resources/icons/GIS_Stream_Data_Shapefile.svg',
    'TI_GENERIC_POINT': ':/resources/icons/GIS_Scatter_Point_Shapefile.svg',
    'TI_GENERIC_POLY': ':/resources/icons/GIS_Polygon_Data_Shapefile.svg',
    'TI_GIS': ':/resources/icons/GIS_Folder.svg',
    # Several different icons in XMS for images based on type of data in the tree item, but for now
    # they all get the raster icon because we don't have access to that information.
    'TI_IMAGE': ':/resources/icons/GIS_Raster_Icon.svg',
    'TI_IMAGE_ONLINE': ':/resources/icons/GIS_Raster_Icon.svg',
    'TI_ROOT_GIS': ':/resources/icons/GIS_Folder.svg',
    'TI_MESH2D': ':/resources/icons/2d_mesh.svg',
    'TI_PROJECT': ':/resources/icons/Project_Icon.svg',
    'TI_QUADTREE': ':/resources/icons/quadtree.svg',
    'TI_ROOT_2DMESH': ':/resources/icons/2d_mesh_folder.svg',
    'TI_ROOT_2DSCAT': ':/resources/icons/2d_scatter_folder.svg',
    'TI_ROOT_QUADTREE': ':/resources/icons/quadtree_folder.svg',
    'TI_ROOT_UGRID': ':/resources/icons/2d_ugrid_folder.svg',
    'TI_SCAT2D': ':/resources/icons/2d_scatter.svg',
    'TI_UGRID_SMS': ':/resources/icons/UGrid_Module_Icon.svg',
    'TI_UGRID': ':/resources/icons/UGrid_Module_Icon.svg',
    'TI_VECTOR_DSET': ':/resources/icons/dataset_vector_active.svg',
    'TI_VFUNC': ':/resources/icons/dataset_vector_active.svg',
}


def get_resource_path(resource_file):
    r"""Convenience method for getting the full path to a resource file.

     Example: ':/resources/icons/add.svg' becomes
              'C:\\Python36\\lib\\site-packages\\xms\\guipy\\resources\\icons\\add.svg'

    Args:
        resource_file (str): Relative path of resource file (e.g. ':/resources/icons/add.svg')

    Returns:
        The full path to the resource file.
    """
    if ':/resources/' in resource_file:
        resource_file = resource_file.replace(':/resources/', '')
    resources_path = os.path.dirname(os.path.abspath(__file__))
    full_path = os.path.join(resources_path, resource_file)
    return os.path.normpath(full_path)


def get_mesh_icon(tree_node):
    """Get the Mesh2D icon for a tree node if it is a mesh item.

    Only works for trees whose root is a Mesh2D tree item

    Args:
        tree_node (TreeNode): The tree item to get overriden icon for

    Returns:
        (str): Path to the icon if we want

    """
    if not tree_node.parent:  # Only overriding icons for the domain Mesh item
        # Use the Mesh2D icon for the root of the tree
        return get_resource_path(':/resources/icons/2d_mesh.svg')
    return ''


def get_quadtree_icon(tree_node):
    """Get the quadtree icon for a tree node if it is a quadtree item.

    Only works for trees whose root is a quadtree tree item

    Args:
        tree_node (TreeNode): The tree item to get overriden icon for

    Returns:
        (str): Path to the icon if we want

    """
    if not tree_node.parent:  # Only overriding icons for the domain Mesh item
        # Use the quadtree icon for the root of the tree
        return get_resource_path(':/resources/icons/quadtree.svg')


def get_tree_icon_from_xms_typename(tree_node):
    """Get an icon for a tree node.

    Args:
        tree_node (TreeNode): The tree item to get overriden icon for

    Returns:
        (str): Path to the icon if we want
    """
    tree_type = tree_node.item_typename
    if tree_type in XMS_TYPE_TO_ICON:
        return get_resource_path(XMS_TYPE_TO_ICON[tree_type])

    # Check dataset location if a scalar dataset.
    if tree_type in ['TI_SFUNC', 'TI_FUNC', 'TI_SCALAR_DSET']:
        if tree_node.data_location == 'NODE':  # Scalar node-based dataset
            return get_resource_path(':/resources/icons/dataset_points_active.svg')
        else:  # Scalar cell-based dataset
            return get_resource_path(':/resources/icons/dataset_cells_active.svg')

    return ''  # Need to add an icon resource for this tree item type and add to XMS_TYPE_TO_ICON.
