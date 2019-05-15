""" Functions for Categorize output file writing."""
import netCDF4
from . import utils, version
from .metadata import COMMON_ATTRIBUTES
from cloudnetpy.products import product_tools


def write_vars2nc(rootgrp, cloudnet_variables, zlib):
    """Iterates over Cloudnet instances and write to given rootgrp."""

    def _get_dimensions(array):
        """Finds correct dimensions for a variable."""
        if utils.isscalar(array):
            return ()
        variable_size = ()
        file_dims = rootgrp.dimensions
        array_dims = array.shape
        for length in array_dims:
            dim = [key for key in file_dims.keys()
                   if file_dims[key].size == length][0]
            variable_size = variable_size + (dim,)
        return variable_size

    for key in cloudnet_variables:
        obj = cloudnet_variables[key]
        size = _get_dimensions(obj.data)
        nc_variable = rootgrp.createVariable(obj.name, obj.data_type, size,
                                             zlib=zlib)
        nc_variable[:] = obj.data
        for attr in obj.fetch_attributes():
            setattr(nc_variable, attr, getattr(obj, attr))


def copy_dimensions(source, target, dim_list):
    """Copies dimensions from one file to another. """
    for dim_name, dimension in source.dimensions.items():
        if dim_name in dim_list:
            target.createDimension(dim_name, len(dimension))


def copy_variables(source, target, var_list):
    """Copies variables (and their attributes) from one file to another."""
    for var_name, variable in source.variables.items():
        if var_name in var_list:
            var_out = target.createVariable(var_name, variable.datatype,
                                            variable.dimensions)
            var_out.setncatts({k: variable.getncattr(k)
                               for k in variable.ncattrs()})
            var_out[:] = variable[:]


def copy_global(source, target, attr_list):
    """Copies global attributes from one file to another."""
    for attr_name in source.ncattrs():
        if attr_name in attr_list:
            setattr(target, attr_name, source.getncattr(attr_name))


def update_attributes(cloudnet_variables, attributes):
    """Overrides existing CloudnetArray-attributes.

    Overrides existing attributes using hard-coded values.
    New attributes are added.

    Args:
        cloudnet_variables (dict): CloudnetArray instances.
        attributes (dict): Product-specific attributes.

    """
    for key in cloudnet_variables:
        if key in attributes:
            cloudnet_variables[key].set_attributes(attributes[key])
        if key in COMMON_ATTRIBUTES:
            cloudnet_variables[key].set_attributes(COMMON_ATTRIBUTES[key])


def init_file(file_name, dimensions, obs, zlib):
    """Initializes a Cloudnet file for writing."""
    root_group = netCDF4.Dataset(file_name, 'w', format='NETCDF4_CLASSIC')
    for key, dimension in dimensions.items():
        root_group.createDimension(key, dimension)
    write_vars2nc(root_group, obs, zlib)
    _add_standard_global_attributes(root_group)
    return root_group


def _add_standard_global_attributes(root_group):
    root_group.Conventions = 'CF-1.7'
    root_group.cloudnetpy_version = version.__version__
    root_group.file_uuid = utils.get_uuid()


def merge_history(root_group, file_type, *sources):
    """Merges history fields from one or several files and creates a new record."""
    new_record = f"{utils.get_time()} - {file_type} file created"
    old_history = ''
    for source in sources:
        old_history += f"\n{source.dataset.history}"
    root_group.history = f"{new_record}{old_history}"


def save_product_file(identifier, obj, file_name, copy_from_cat=()):
    """Saves a standard Cloudnet product file."""
    dims = {'time': len(obj.time), 'height': len(obj.variables['height'])}
    root_group = init_file(file_name, dims, obj.data, zlib=True)
    vars_from_source = ('altitude', 'latitude', 'longitude', 'time', 'height') + copy_from_cat
    copy_variables(obj.dataset, root_group, vars_from_source)
    root_group.title = f"{identifier.capitalize()} file from {obj.dataset.location}"
    root_group.source = f"Categorize file: {product_tools.get_source(obj)}"
    copy_global(obj.dataset, root_group, ('location', 'day', 'month', 'year'))
    merge_history(root_group, identifier, obj)
    root_group.close()
