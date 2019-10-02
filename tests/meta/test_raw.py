"""Tests for raw radar/lidar files, and model / hatpro files."""
import pytest

REQUIRED_VARIABLES = {
    'mira_raw':
        {'prf', 'NyquistVelocity', 'time', 'range', 'Zg', 'VELg', 'RMSg',
         'LDRg', 'SNRg'},
    'chm15k_raw':
        {'time', 'range', 'beta_raw', 'zenith', 'wavelength'},
    'hatpro':
        {'time', 'LWP_data', 'elevation_angle'},
    'ecmwf':
        {'temperature', 'pressure', 'rh', 'gas_atten', 'specific_gas_atten',
         'specific_saturated_gas_atten', 'specific_liquid_atten', 'q', 'uwind',
         'vwind', 'height', 'time'}
}

REQUIRED_ATTRIBUTES = {
    'mira_raw':
        {'Latitude', 'Longitude'},
    'chm15k_raw':
        {'year', 'month', 'day'},
    'hatpro':
        {'station_altitude'},
    'ecmwf':
        {'history'}
}


@pytest.mark.mira_raw
class TestMiraRaw:
    name = 'mira_raw'

    def test_variables(self, variable_names):
        assert not REQUIRED_VARIABLES[self.name] - variable_names

    def test_attributes(self, global_attribute_names):
        assert not REQUIRED_ATTRIBUTES[self.name] - global_attribute_names


@pytest.mark.chm15k_raw
class TestChm15kRaw:
    name = 'chm15k_raw'

    def test_variables(self, variable_names):
        assert not REQUIRED_VARIABLES[self.name] - variable_names

    def test_attributes(self, global_attribute_names):
        assert not REQUIRED_ATTRIBUTES[self.name] - global_attribute_names


@pytest.mark.hatpro
class TestHatpro:
    name = 'hatpro'

    def test_variables(self, variable_names):
        assert not REQUIRED_VARIABLES[self.name] - variable_names

    def test_attributes(self, global_attribute_names):
        assert not REQUIRED_ATTRIBUTES[self.name] - global_attribute_names


@pytest.mark.ecmwf
class TestEcmwf:
    name = 'ecmwf'

    def test_variables(self, variable_names):
        assert not REQUIRED_VARIABLES[self.name] - variable_names

    def test_attributes(self, global_attribute_names):
        assert not REQUIRED_ATTRIBUTES[self.name] - global_attribute_names

