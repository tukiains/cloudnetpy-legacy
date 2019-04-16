"""General helper functions for all products."""
import numpy as np
import netCDF4
from datetime import time, datetime
import cloudnetpy.utils as utils


def read_quality_bits(categorize_object):
    bitfield = categorize_object.getvar('quality_bits')
    keys = _get_quality_keys()
    return check_active_bits(bitfield, keys)


def read_category_bits(categorize_object):
    bitfield = categorize_object.getvar('category_bits')
    keys = _get_category_keys()
    return check_active_bits(bitfield, keys)


def check_active_bits(bitfield, keys):
    """
    Converts bitfield into dictionary.

    Args:
        bitfield (int): Array of integers containing yes/no
            information coded in the individual bits.

        keys (array_like): list of strings containing the names of the bits.
            They will be the keys in the returned dictionary.

    Returns:
        dict: Individual bits in a dictionary (with proper names).

    """
    bits = {}
    for i, key in enumerate(keys):
        bits[key] = utils.isbit(bitfield, i)
    return bits


def _get_category_keys():
    """Returns names of the 'category_bits' bits."""
    return ('droplet', 'falling', 'cold',
            'melting', 'aerosol', 'insect')


def _get_quality_keys():
    """Returns names of the 'quality_bits' bits."""
    return ('radar', 'lidar', 'clutter', 'molecular',
            'attenuated', 'corrected')


def get_source(data_handler):
    """Returns uuid (or filename if uuid not found) of the source file."""
    return getattr(data_handler.dataset, 'file_uuid', data_handler.filename)


def get_correct_dimensions(nc_file, field_names):
    """ Check if "model"-dimension exist. if not
        change model-dimension to normal dimension
    """
    variables = netCDF4.Dataset(nc_file).variables
    field_names = list(field_names)
    for i in range(len(field_names)):
        if field_names[i] not in variables:
            name = field_names[i].split('_')
            field_names[i] = name[-1]
    return tuple(field_names)


def read_nc_fields(nc_file, field_names):
    """Reads selected variables from a netCDF file and returns as a list."""
    nc_variables = netCDF4.Dataset(nc_file).variables
    return [nc_variables[name][:] for name in field_names]


def convert_dtime_to_datetime(case_date, time_array):
    """Converts decimal time and date to datetime."""
    time_array = [_dtime2time(t) for t in time_array]
    time_array = [datetime.combine(case_date, t) for t in time_array]
    return np.asanyarray(time_array)


def _dtime2time(t):
    hour = int(t)
    minute = int((t*60) % 60)
    sec = int((t*3600) % 60)
    return time(hour, minute, sec)
