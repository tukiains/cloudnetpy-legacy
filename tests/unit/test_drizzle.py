from unittest import TestCase

import numpy as np
from numpy import testing
from collections import namedtuple
import pytest
from pathlib import Path
import netCDF4
import cloudnetpy.products.drizzle as drizzle
from cloudnetpy.products.drizzle import *

DIMENSIONS_X = ('time', 'model_time')
TEST_ARRAY_X = np.arange(2)
DIMENSIONS_Y = ('height', 'model_height')
TEST_ARRAY_Y = np.arange(3)


@pytest.fixture(scope='session')
def drizzle_source_file(tmpdir_factory, file_metadata):
    file_name = tmpdir_factory.mktemp("data").join("file.nc")
    root_grp = netCDF4.Dataset(file_name, "w", format="NETCDF4_CLASSIC")
    _create_dimensions(root_grp, TEST_ARRAY_X, DIMENSIONS_X)
    _create_dimension_variables(root_grp, TEST_ARRAY_X, DIMENSIONS_X)
    _create_dimensions(root_grp, TEST_ARRAY_Y, DIMENSIONS_Y)
    _create_dimension_variables(root_grp, TEST_ARRAY_Y, DIMENSIONS_Y)
    var = root_grp.createVariable('altitude', 'f8')
    var[:] = 1
    var.units = 'km'
    var = root_grp.createVariable('beta', 'f8', ('time', 'height'))
    var[:] = [[0.1, 0.1, 0.1], [1, 0.2, 3]]
    var = root_grp.createVariable('v', 'f8', ('time', 'height'))
    var[:] = [[1, 2, 3], [1, 2, 3]]
    var = root_grp.createVariable('Z', 'f8', ('time', 'height'))
    var[:] = [[1, 0.1, 0.2], [0.3, 2, 0.1]]
    var = root_grp.createVariable('category_bits', 'i4', ('time', 'height'))
    var[:] = [[0, 1, 2], [4, 8, 16]]
    var = root_grp.createVariable('quality_bits', 'i4', ('time', 'height'))
    var[:] = [[0, 1, 2], [4, 8, 16]]
    var = root_grp.createVariable('radar_frequency', 'f8')
    var[:] = 35.5  # TODO: How to check with multiple options
    root_grp.close()
    return file_name


def _create_dimensions(root_grp, test_array, dimension):
    n_dim = len(test_array)
    for dim_name in dimension:
        root_grp.createDimension(dim_name, n_dim)


def _create_dimension_variables(root_grp, test_array, dimension):
    for dim_name in dimension:
        x = root_grp.createVariable(dim_name, 'f8', (dim_name,))
        x[:] = test_array
        if dim_name == 'height':
            x.units = 'm'


def test_convert_z_units(drizzle_source_file):
    from cloudnetpy.utils import db2lin
    obj = DrizzleSource(drizzle_source_file)
    z = obj.getvar('Z') - 180
    compare = db2lin(z)
    testing.assert_array_almost_equal(obj._convert_z_units(), compare)


@pytest.mark.parametrize('key',
                         ['Do', 'mu', 'S', 'lwf', 'termv', 'width', 'ray', 'v'])
def test_read_mie_lut(drizzle_source_file, key):
    obj = DrizzleSource(drizzle_source_file)
    assert key in obj.mie.keys()


def test_get_mie_file(drizzle_source_file):
    obj = DrizzleSource(drizzle_source_file)
    obj.module_path = ''.join((str(Path(__file__).parents[2]), '/cloudnetpy/products/'))
    obj._get_mie_file()
    compare = '/'.join((obj.module_path, 'mie_lu_tables.nc'))
    testing.assert_equal(obj._get_mie_file(), compare)


def test_get_wl_band(drizzle_source_file):
    obj = DrizzleSource(drizzle_source_file)
    compare = '35'
    testing.assert_equal(obj._get_wl_band(), compare)


@pytest.fixture(scope='session')
def drizzle_cat_file(tmpdir_factory, file_metadata):
    file_name = tmpdir_factory.mktemp("data").join("file.nc")
    root_grp = netCDF4.Dataset(file_name, "w", format="NETCDF4_CLASSIC")
    _create_dimensions(root_grp, TEST_ARRAY_X, DIMENSIONS_X)
    _create_dimension_variables(root_grp, TEST_ARRAY_X, DIMENSIONS_X)
    _create_dimensions(root_grp, TEST_ARRAY_Y, DIMENSIONS_Y)
    _create_dimension_variables(root_grp, TEST_ARRAY_Y, DIMENSIONS_Y)
    var = root_grp.createVariable('dheight', 'f8')
    var[:] = 10
    var = root_grp.createVariable('uwind', 'f8', ('model_time', 'model_height'))
    var[:] = [[2, 2, 1], [1, 3, 5]]
    var = root_grp.createVariable('vwind', 'f8', ('model_time', 'model_height'))
    var[:] = [[-2, -2, 1], [1, -3, 0]]
    var = root_grp.createVariable('category_bits', 'i4', ('time', 'height'))
    var[:] = [[0, 1, 2], [4, 8, 16]]
    var = root_grp.createVariable('quality_bits', 'i4', ('time', 'height'))
    var[:] = [[0, 1, 2], [4, 8, 16]]
    var = root_grp.createVariable('is_rain', 'i4', 'time')
    var[:] = [0, 1]
    var = root_grp.createVariable('is_undetected_melting', 'i4', 'time')
    var[:] = [0, 1]
    var = root_grp.createVariable('v_sigma', 'f8', ('time', 'height'))
    var[:] = [[-2, np.nan, 2], [1, -1, 0]]
    var = root_grp.createVariable('width', 'f8', ('time', 'height'))
    var[:] = [[2, 0, 1], [1, 3, 0]]
    root_grp.close()
    return file_name


def test_find_v_sigma(drizzle_cat_file):
    obj = DrizzleClassification(drizzle_cat_file)
    compare = np.array([[1, 0, 1], [1, 1, 1]], dtype=bool)
    testing.assert_array_almost_equal(obj._find_v_sigma(drizzle_cat_file), compare)


def test_find_warm_liquid(drizzle_cat_file):
    obj = DrizzleClassification(drizzle_cat_file)
    obj.category_bits['droplet'] = np.array([0, 0, 0, 1, 1, 1, 0], dtype=bool)
    obj.category_bits['cold'] = np.array([1, 1, 0, 0, 1, 0, 1], dtype=bool)
    compare = np.array([0, 0, 0, 1, 0, 1, 0], dtype=bool)
    testing.assert_array_almost_equal(obj._find_warm_liquid(), compare)


@pytest.mark.parametrize("is_rain, falling, droplet, cold, melting, insect, "
     "radar, lidar, clutter, molecular, attenuated, v_sigma", [
         (np.array([0, 0, 0, 0]), np.array([1, 1, 1, 1]),
          np.array([0, 0, 0, 1]), np.array([0, 0, 0, 1]),
          np.array([0, 0, 0, 1]), np.array([0, 0, 0, 0]),
          np.array([1, 1, 1, 1]), np.array([1, 1, 1, 1]),
          np.array([0, 0, 0, 1]), np.array([0, 0, 0, 1]),
          np.array([0, 0, 0, 1]), np.array([1, 1, 0, 1]))])
def test_find_drizzle(drizzle_cat_file, is_rain, falling, droplet, cold, melting,
                      insect, radar, lidar, clutter, molecular, attenuated, v_sigma):
    obj = DrizzleClassification(drizzle_cat_file)
    obj.is_rain = is_rain
    obj.category_bits['falling'] = falling
    obj.category_bits['droplet'] = droplet
    obj.category_bits['cold'] = cold
    obj.category_bits['melting'] = melting
    obj.category_bits['insect'] = insect
    obj.quality_bits['radar'] = radar
    obj.quality_bits['lidar'] = lidar
    obj.quality_bits['clutter'] = clutter
    obj.quality_bits['molecular'] = molecular
    obj.quality_bits['attenuated'] = attenuated
    obj.is_v_sigma = v_sigma
    compare = np.array([[1, 1, 0, 0],
                        [1, 1, 0, 0],
                        [1, 1, 0, 0],
                        [1, 1, 0, 0]])
    testing.assert_array_almost_equal(obj._find_drizzle(), compare)


@pytest.mark.parametrize("is_rain, warm, falling, melting, insect, "
     "radar, clutter, molecular", [
         (np.array([0, 0, 0, 0]), np.array([1, 1, 1, 1]),
          np.array([1, 1, 1, 0]), np.array([0, 0, 0, 1]),
          np.array([0, 0, 0, 1]), np.array([0, 1, 1, 0]),
          np.array([0, 0, 0, 1]), np.array([0, 0, 0, 1]))])
def test_find_would_be_drizzle(drizzle_cat_file, is_rain, warm, falling, melting,
                               insect, radar, clutter, molecular):
    obj = DrizzleClassification(drizzle_cat_file)
    obj.is_rain = is_rain
    obj.warm_liquid = warm
    obj.category_bits['falling'] = falling
    obj.category_bits['melting'] = melting
    obj.category_bits['insect'] = insect
    obj.quality_bits['radar'] = radar
    obj.quality_bits['clutter'] = clutter
    obj.quality_bits['molecular'] = molecular
    compare = np.array([[0, 1, 1, 0],
                        [0, 1, 1, 0],
                        [0, 1, 1, 0],
                        [0, 1, 1, 0]])
    testing.assert_array_almost_equal(obj._find_would_be_drizzle(), compare)


def test_find_cold_rain(drizzle_cat_file):
    obj = DrizzleClassification(drizzle_cat_file)
    compare = np.array([0, 1])
    testing.assert_array_almost_equal(obj._find_cold_rain(), compare)


def test_calculate_spectral_width(drizzle_cat_file):
    obj = CorrectSpectralWidth(drizzle_cat_file)
    width = netCDF4.Dataset(drizzle_cat_file).variables['width'][:]
    v_sigma = netCDF4.Dataset(drizzle_cat_file).variables['v_sigma'][:]
    factor = obj._calc_v_sigma_factor()
    compare = width - factor * v_sigma
    testing.assert_almost_equal(obj.calculate_spectral_width(), compare)


def test_calc_beam_divergence(drizzle_cat_file):
    obj = CorrectSpectralWidth(drizzle_cat_file)
    height = netCDF4.Dataset(drizzle_cat_file).variables['height'][:]
    compare = height * np.deg2rad(0.5)
    testing.assert_almost_equal(obj._calc_beam_divergence(), compare)


def test_calc_v_sigma_factor(drizzle_cat_file):
    from cloudnetpy.utils import l2norm
    obj = CorrectSpectralWidth(drizzle_cat_file)
    height = netCDF4.Dataset(drizzle_cat_file).variables['height'][:]
    uwind = netCDF4.Dataset(drizzle_cat_file).variables['uwind'][:]
    vwind = netCDF4.Dataset(drizzle_cat_file).variables['vwind'][:]
    beam = height * np.deg2rad(0.5)
    wind = l2norm(uwind, vwind)
    a_wind = (wind + beam) ** (2 / 3)
    s_wind = (30 * wind + beam) ** (2 / 3)
    compare = a_wind / (s_wind - a_wind)
    testing.assert_array_almost_equal(obj._calc_v_sigma_factor(), compare)


def test_calc_horizontal_wind(drizzle_cat_file):
    from cloudnetpy.utils import l2norm
    obj = CorrectSpectralWidth(drizzle_cat_file)
    uwind = netCDF4.Dataset(drizzle_cat_file).variables['uwind'][:]
    vwind = netCDF4.Dataset(drizzle_cat_file).variables['vwind'][:]
    compare = l2norm(uwind, vwind)
    testing.assert_array_almost_equal(obj._calc_horizontal_wind(), compare)


# Create objects for all coming tests witch uses these classes
@pytest.fixture(scope='session')
def class_objects(drizzle_source_file, drizzle_cat_file):
    drizzle_source = DrizzleSource(drizzle_source_file)
    drizzle_class = DrizzleClassification(drizzle_cat_file)
    spectral_w = CorrectSpectralWidth(drizzle_cat_file)
    return [drizzle_source, drizzle_class, spectral_w]


def test_init_variables(class_objects):
    d_source, d_class, s_width = class_objects
    obj = DrizzleSolving(d_source, d_class, s_width)
    assert True


def test_calc_beta_z_ratio(class_objects):
    d_source, d_class, s_width = class_objects
    obj = DrizzleSolving(d_source, d_class, s_width)
    assert True


def test_find_lut_indices(class_objects):
    d_source, d_class, s_width = class_objects
    obj = DrizzleSolving(d_source, d_class, s_width)
    assert True


def test_update_result_tables(class_objects):
    d_source, d_class, s_width = class_objects
    obj = DrizzleSolving(d_source, d_class, s_width)
    assert True


def test_is_converged(class_objects):
    d_source, d_class, s_width = class_objects
    obj = DrizzleSolving(d_source, d_class, s_width)
    assert True


def test_calc_dia(class_objects):
    d_source, d_class, s_width = class_objects
    obj = DrizzleSolving(d_source, d_class, s_width)
    assert True


def test_solve_drizzle(class_objects):
    d_source, d_class, s_width = class_objects
    obj = DrizzleSolving(d_source, d_class, s_width)
    assert True






@pytest.mark.parametrize("x, result", [
    (-1000, -1),
    (-100, -0.99999),
    (-10, -0.9),
    (-1, np.exp(-1 / 10 * np.log(10)) - 1),
])
def test_db2lin(x, result):
    testing.assert_array_almost_equal(drizzle.db2lin(x), result, decimal=5)


def test_db2lin_raise():
    with pytest.raises(ValueError):
        drizzle.db2lin(150)


@pytest.mark.parametrize("x, result", [
    (1e6, 60),
    (1e5, 50),
    (1e4, 40),
])
def test_lin2db(x, result):
    testing.assert_array_almost_equal(drizzle.lin2db(x), result, decimal=3)


def test_lin2db_raise():
    with pytest.raises(ValueError):
        drizzle.lin2db(-1)


def test_get_drizzle_indices():
    dia = np.array([-1, 2 * 1e-5, 1, 1e-6])
    d = drizzle.CalculateErrors._get_drizzle_indices(dia)
    correct = {'drizzle': [False, True, True, True],
               'small': [False, True, False, False],
               'tiny': [False, False, False, True]}
    for key in d.keys():
        testing.assert_array_equal(d[key], correct[key])
