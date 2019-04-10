"""Module for reading and processing Vaisala ceilometers."""
import linecache
import numpy as np
import numpy.ma as ma
import scipy.ndimage
from cloudnetpy import utils

# from collections import namedtuple
# from cloudnetpy import plotting
# import matplotlib.pyplot as plt
# import sys


M2KM = 0.001


class VaisalaCeilo:
    """Base class for Vaisala ceilometers."""
    def __init__(self, file_name):
        self.file_name = file_name
        self.model = None
        self.message_number = None
        self._hex_conversion_params = None
        self.noise_params = None
        self.backscatter = None
        self._backscatter_scale_factor = None
        self.metadata = None
        self.range = None
        self.time = None

    def _fetch_data_lines(self):
        """Finds data lines (header + backscatter) from ceilometer file."""
        with open(self.file_name) as file:
            all_lines = file.readlines()
        return self._screen_empty_lines(all_lines)

    def _read_header_line_1(self, lines):
        """Reads all first header lines from CT25k and CL ceilometers."""
        keys = ('model_id', 'unit_id', 'software_version', 'message_number',
                'message_subclass')
        values = []
        if 'cl' in self.model:
            indices = [1, 3, 4, 7, 8, 9]
        else:
            indices = [1, 3, 4, 6, 7, 8]
        for line in lines:
            distinct_values = _split_string(line, indices)
            values.append(distinct_values)
        return _values_to_dict(keys, values)

    def _calc_range(self):
        if self.model == 'ct25k':
            range_resolution = 30
            n_gates = 256
        else:
            n_gates = int(self.metadata['number_of_gates'])
            range_resolution = int(self.metadata['range_resolution'])
        return np.arange(1, n_gates + 1) * range_resolution

    def _read_backscatter(self, lines):
        n_chars = self._hex_conversion_params[0]
        n_gates = int(len(lines[0])/n_chars)
        profiles = np.zeros((len(lines), n_gates), dtype=int)
        ran = range(0, n_gates*n_chars, n_chars)
        for ind, line in enumerate(lines):
            try:
                profiles[ind, :] = [int(line[i:i+n_chars], 16) for i in ran]
            except ValueError as error:
                print(error)

        ind = np.where(profiles & self._hex_conversion_params[1] != 0)
        profiles[ind] -= self._hex_conversion_params[2]
        return profiles.astype(float) / self._backscatter_scale_factor

    @staticmethod
    def _screen_empty_lines(data):
        """Removes empty lines from the list of data."""

        def _parse_empty_lines():
            return [n for n, _ in enumerate(data) if is_empty_line(data[n])]

        def _parse_data_lines(empty_indices):
            number_of_data_lines = empty_indices[1] - empty_indices[0] - 1
            lines = []
            for line_number in range(number_of_data_lines):
                lines.append([data[n + line_number + 1] for n in empty_indices])
            return lines

        empty_lines = _parse_empty_lines()
        return _parse_data_lines(empty_lines)

    @staticmethod
    def _read_header_line_2(lines):
        """Same for all data messages."""
        keys = ('detection_status', 'warning', 'cloud_base_data', 'warning_flags')
        values = []
        for line in lines:
            distinct_values = [line[0], line[1], line[3:20], line[21:].strip()]
            values.append(distinct_values)
        return _values_to_dict(keys, values)

    @staticmethod
    def _get_message_number(header_line_1):
        msg_no = header_line_1['message_number']
        assert len(np.unique(msg_no)) == 1, 'Error: inconsistent message numbers.'
        return int(msg_no[0])

    @staticmethod
    def _calc_time(time_lines):
        time = [time_to_fraction_hour(line.split()[1]) for line in time_lines]
        return np.array(time)

    @classmethod
    def _handle_metadata(cls, header):
        meta = cls._concatenate_meta(header)
        meta = cls._remove_meta_duplicates(meta)
        meta = cls._convert_meta_strings(meta)
        return meta

    @staticmethod
    def _concatenate_meta(header):
        meta = {}
        for head in header:
            meta = {**meta, **head}
        return meta

    @staticmethod
    def _remove_meta_duplicates(meta):
        for field in meta:
            if len(np.unique(meta[field])) == 1:
                meta[field] = meta[field][0]
        return meta

    @staticmethod
    def _convert_meta_strings(meta):
        int_variables = ('tilt_angle', 'message_number', 'scale')
        for field in meta:
            values = meta[field]
            if isinstance(values, str):
                if field in int_variables:
                    meta[field] = int(values)
            else:
                meta[field] = [None] * len(meta[field])
                for ind, value in enumerate(values):
                    try:
                        meta[field][ind] = int(value)
                    except (ValueError, TypeError):
                        continue
        return meta

    def _read_header_line_3(self, data):
        raise NotImplementedError

    def _read_common_header_part(self):
        header = []
        data_lines = self._fetch_data_lines()
        self.time = self._calc_time(data_lines[0])
        header.append(self._read_header_line_1(data_lines[1]))
        self.message_number = self._get_message_number(header[0])
        header.append(self._read_header_line_2(data_lines[2]))
        header.append(self._read_header_line_3(data_lines[3]))
        return header, data_lines


class ClCeilo(VaisalaCeilo):
    """Base class for Vaisala CL31/CL51 ceilometers."""

    def __init__(self, file_name):
        super().__init__(file_name)
        self._hex_conversion_params = (5, 524288, 1048576)
        self._backscatter_scale_factor = 1e8
        self.noise_params = (100, 1e-12, 3e-6, (1.1e-8, 2.9e-8))

    def read_ceilometer_file(self):
        """Read all lines of data from the file."""
        header, data_lines = self._read_common_header_part()
        header.append(self._read_header_line_4(data_lines[-3]))
        self.metadata = self._handle_metadata(header)
        self.backscatter = self._read_backscatter(data_lines[-2])
        self.range = self._calc_range()  # this is duplicate, should be elsewhere

    def _read_header_line_3(self, lines):
        if self.message_number != 2:
            return None
        keys = ('cloud_detection_status', 'cloud_amount_data')
        values = []
        for line in lines:
            distinct_values = [line[0:3], line[3:].strip()]
            values.append(distinct_values)
        return _values_to_dict(keys, values)

    @staticmethod
    def _read_header_line_4(lines):
        keys = ('scale', 'range_resolution', 'number_of_gates', 'laser_energy',
                'laser_temperature', 'window_transmission', 'tilt_angle',
                'background_light', 'measurement_parameters', 'backscatter_sum')
        values = []
        for line in lines:
            values.append(line.split())
        return _values_to_dict(keys, values)


class Cl51(ClCeilo):
    """Class for Vaisala CL51 ceilometer."""
    def __init__(self, input_file):
        super().__init__(input_file)
        self.model = 'cl51'


class Cl31(ClCeilo):
    """Class for Vaisala CL31 ceilometer."""
    def __init__(self, input_file):
        super().__init__(input_file)
        self.model = 'cl31'


class Ct25k(VaisalaCeilo):
    """Class for Vaisala CT25k ceilometer.

    References:
        https://www.manualslib.com/manual/1414094/Vaisala-Ct25k.html

    """
    def __init__(self, input_file):
        super().__init__(input_file)
        self.model = 'ct25k'
        self._hex_conversion_params = (4, 32768, 65536)
        self._backscatter_scale_factor = 1e7
        self.noise_params = (40, 2e-14, 0.3e-6, (3e-10, 1.5e-9))

    def read_ceilometer_file(self):
        """Read all lines of data from the file."""
        header, data_lines = self._read_common_header_part()
        self.metadata = self._handle_metadata(header)
        hex_profiles = self._parse_hex_profiles(data_lines[4:20])
        self.backscatter = self._read_backscatter(hex_profiles)
        self.range = self._calc_range()  # this is duplicate, should be elsewhere
        self._range_correct_upper_part()

    def _range_correct_upper_part(self):
        """In CT25k only altitudes below 2.4 km are range corrected"""
        altitude_limit = 2400
        ind = np.where(self.range > altitude_limit)
        self.backscatter[:, ind] *= (self.range[ind]*M2KM)**2

    @staticmethod
    def _parse_hex_profiles(lines):
        """Collects ct25k profiles into list (one profile / element)."""
        n_profiles = len(lines[0])
        return [''.join([lines[l][n][3:].strip() for l in range(16)])
                for n in range(n_profiles)]

    def _read_header_line_3(self, lines):
        if self.message_number in (1, 3, 6):
            return None
        keys = ('scale', 'measurement_mode', 'laser_energy',
                'laser_temperature', 'receiver_sensitivity',
                'window_contamination', 'tilt_angle', 'background_light',
                'measurement_parameters', 'backscatter_sum')
        values = []
        for line in lines:
            values.append(line.split())
        return _values_to_dict(keys, values)


def ceilo2nc(input_file, output_file):
    """Converts Vaisala ceilometer txt-file to netCDF."""
    ceilo = _initialize_ceilo(input_file)
    ceilo.read_ceilometer_file()
    beta, beta_smooth = calc_beta(ceilo)


def calc_beta(ceilo):
    """From raw beta to beta."""

    def _screening_wrapper(beta_in, smooth):
        beta_in = _uncorrect_range(beta_in, range_squared)
        beta_in = _screen_by_snr(beta_in, ceilo, is_saturation, smooth=smooth)
        return _correct_range(beta_in, range_squared)

    range_squared = _get_range_squared(ceilo)
    is_saturation = _find_saturated_profiles(ceilo)
    beta = _screening_wrapper(ceilo.backscatter, False)
    # smoothed version:
    beta_smooth = ma.copy(beta)
    cloud_ind, cloud_values = _estimate_clouds_from_beta(beta)
    sigma = _calc_sigma_units(ceilo)
    beta_smooth = scipy.ndimage.filters.gaussian_filter(beta_smooth, sigma)
    beta_smooth[cloud_ind] = cloud_values
    beta_smooth = _screening_wrapper(beta_smooth, True)
    return beta, beta_smooth


def _estimate_clouds_from_beta(beta):
    """Naively finds strong clouds from ceilometer backscatter."""
    cloud_limit = 1e-6
    cloud_ind = np.where(beta > cloud_limit)
    return cloud_ind, beta[cloud_ind]


def _screen_by_snr(beta_uncorrected, ceilo, is_saturation, smooth=False, snr_lim=5):
    """ beta needs to be range-UN-corrected.

    Args:
        beta (ndarray): Range-uncorrected backscatter.
        ceilo (obj): Ceilometer object.
        is_saturation (ndarray): Boolean array denoting saturated profiles.
        smooth (bool): Should be true if input beta is smoothed. Default is False.
        snr_lim (int): SNR limit for screening. Default is 5.
    """

    beta = ma.copy(beta_uncorrected)
    n_gates, _, saturation_noise, noise_min = ceilo.noise_params
    noise_min = noise_min[0] if smooth else noise_min[1]

    # Too small noise would be problem.
    noise_at_top = np.std(beta[:, -n_gates:], axis=1)
    noise_at_top[np.where(noise_at_top < noise_min)] = noise_min

    # Low values in saturated profiles above peak are noise.
    for ind in np.where(is_saturation)[0]:
        prof = beta[ind, :]
        peak_ind = np.argmax(prof)
        noise_indices = np.where(prof[peak_ind:] < saturation_noise)[0] + peak_ind
        beta[ind, noise_indices] = 0

    snr = (beta.T / noise_at_top)
    beta[snr.T < snr_lim] = 0.0
    return beta


def _get_range_squared(ceilo):
    """Returns range squared (km2)."""
    return (ceilo.range*M2KM)**2


def _uncorrect_range(beta, range_squared):
    """Return range-uncorrected backscatter."""
    return beta / range_squared


def _correct_range(beta, range_squared):
    """Return range-corrected backscatter."""
    return beta * range_squared


def _find_saturated_profiles(ceilo):
    """Estimates saturated profiles using the variance of the top range gates."""
    n_gates, var_lim, _, _ = ceilo.noise_params
    var = np.var(ceilo.backscatter[:, -n_gates:], axis=1)
    return var < var_lim


def _calc_sigma_units(ceilo):
    """Calculates Gaussian peak std parameters."""
    sigma = (2, 5)
    time_step = utils.mdiff(ceilo.time) * 60
    alt_step = utils.mdiff(ceilo.range)
    x = sigma[0] / time_step
    y = sigma[1] / alt_step
    return x, y


def _values_to_dict(keys, values):
    out = {}
    for i, key in enumerate(keys):
        out[key] = np.array([x[i] for x in values])
    return out


def _split_string(string, indices):
    """Split string between indices."""
    return [string[n:m] for n, m in zip(indices[:-1], indices[1:])]


def _initialize_ceilo(file):
    model = _find_ceilo_model(file)
    if model == 'cl51':
        return Cl51(file)
    elif model == 'cl31':
        return Cl31(file)
    return Ct25k(file)


def _find_ceilo_model(file):
    first_empty_line = _find_first_empty_line(file)
    hint = linecache.getline(file, first_empty_line + 2)[1:5]
    if hint == 'CL01':
        return 'cl51'
    elif hint == 'CL02':
        return 'cl31'
    elif hint == 'CT02':
        return 'ct25k'
    return None


def _find_first_empty_line(file_name):
    line_number = 1
    with open(file_name) as file:
        for line in file:
            if is_empty_line(line):
                break
            line_number += 1
    return line_number


def is_empty_line(line):
    """Tests if line in text file is empty."""
    if line in ('\n', '\r\n'):
        return True
    return False


def time_to_fraction_hour(time):
    """ Time (hh:mm:ss) as fraction hour """
    h, m, s = time.split(':')
    return int(h) + (int(m) * 60 + int(s)) / 3600
