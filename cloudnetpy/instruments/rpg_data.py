"""Module aiming to implement a generic RPG data reader."""
import numpy as np
from cloudnetpy.instruments.rpg_header import read_rpg_header, get_rpg_file_type


class RpgBin:
    """RPG Cloud Radar Level 0/1 Version 2/3 data reader."""
    def __init__(self, filename):
        self.filename = filename
        self.header, self._file_position = read_rpg_header(filename)
        self.level, self.version = get_rpg_file_type(self.header)
        self.data = self.read_rpg_data()

    def read_rpg_data(self):
        """Reads the actual data from rpg binary file."""

        def _init_float_blocks():
            block_one = np.zeros((n_profiles, n_floats))
            if self.level == 1:
                block_two = np.zeros((n_profiles,
                                      self.header['n_range_levels'],
                                      len(dict2)))
            else:
                max_len = max(self.header['n_spectral_samples']) * len(dict2)
                block_two = np.zeros((n_profiles,
                                      self.header['n_range_levels'],
                                      max_len))
            return block_one, block_two

        file = open(self.filename, 'rb')
        file.seek(self._file_position)
        n_profiles = int(np.fromfile(file, np.int32, 1))
        dict0 = _create_dict0(n_profiles)
        dict1 = _create_dict1()
        dict2 = _create_dict2(self.level, self.header)
        n_floats = _get_float_block_length(self.level, self.header, dict1)
        float_block1, float_block2 = _init_float_blocks()
        n_samples_at_each_height = _get_n_samples(self.header)

        for prof in range(n_profiles):

            dict0['sample_length'][prof] = np.fromfile(file, np.int32, 1)
            dict0['time'][prof] = np.fromfile(file, np.uint32, 1)
            dict0['time_ms'][prof] = np.fromfile(file, np.int32, 1)
            dict0['quality_flag'][prof] = np.fromfile(file, np.int8, 1)
            float_block1[prof, :] = np.fromfile(file, np.float32, n_floats)
            is_data_ind = np.where(np.fromfile(file, np.int8,
                                               self.header['n_range_levels']))[0]

            if self.level == 1:

                n_valid, n_keys = len(is_data_ind), len(dict2)
                values = np.fromfile(file, np.float32, n_keys * n_valid)
                float_block2[prof, is_data_ind, :] = values.reshape(n_valid,
                                                                    n_keys)

            elif self.header['compression'] == 0:

                n_keys = len(dict2)
                n_samples = n_samples_at_each_height[is_data_ind]
                dtype = ' '.join([f"int32, ({n_keys*x},)float32, " for x in n_samples])
                data_chunk = np.array(np.fromfile(file, np.dtype(dtype), 1)[0].tolist())[1::2]
                for alt_ind, data in zip(is_data_ind, data_chunk):
                    float_block2[prof, alt_ind, :n_samples_at_each_height[alt_ind]] = data

            else:

                for _ in is_data_ind:

                    n_bytes_in_block = np.fromfile(file, np.int32, 1)
                    n_blocks = int(np.fromfile(file, np.int8, 1)[0])
                    min_ind, max_ind = np.fromfile(file, np.dtype(f"({n_blocks}, )int16"), 2)
                    n_indices = max_ind - min_ind

                    n_values = (sum(n_indices) + len(n_indices)) * 4 + 2
                    all_data = np.fromfile(file, np.float32, n_values)

                    if self.header['anti_alias'] == 1:
                        is_anti_applied, min_velocity = np.fromfile(file, np.dtype('int8, float32'), 1)[0]

        file.close()

        for n, name in enumerate(dict1):
            dict1[name] = float_block1[:, n]

        if self.level == 1:
            for n, name in enumerate(dict2):
                dict2[name] = float_block2[:, :, n]

        elif self.header['compression'] == 0:

            n_keys = len(dict2)
            for key in dict2:
                dict2[key] = np.zeros((n_profiles, self.header['n_range_levels'],
                                       max(self.header['n_spectral_samples'])))

            for n_spec in np.unique(self.header['n_spectral_samples']):
                ind = np.where(n_samples_at_each_height == n_spec)[0]
                blocks = np.split(float_block2[:, ind, :n_spec*n_keys], n_keys)
                for name, block in zip(dict2, blocks):
                    dict2[name][:, ind, :n_spec] = block

        return {**dict0, **dict1, **dict2}


def _get_n_samples(header):
    """Finds number of spectral samples at each height."""
    array = np.ones(header['n_range_levels'], dtype=int)
    sub_arrays = np.split(array, header['chirp_start_indices'][1:])
    sub_arrays *= header['n_spectral_samples']
    return np.concatenate(sub_arrays)


def _create_dict0(n_profiles):
    """Initializes dictionaries for data arrays."""
    return {'sample_length': np.zeros(n_profiles, np.int),
            'time': np.zeros(n_profiles, np.int),
            'time_ms': np.zeros(n_profiles, np.int),
            'quality_flag': np.zeros(n_profiles, np.int)}


def _create_dict1():
    return dict.fromkeys((
        'rain_rate',
        'relative_humidity',
        'temperature',
        'pressure',
        'wind_speed',
        'wind_direction',
        'voltage',
        'brightness_temperature',
        'lwp',
        'if_power',
        'elevation',
        'azimuth',
        'status_flag',
        'transmitted_power',
        'transmitter_temperature',
        'receiver_temperature',
        'pc_temperature'))


def _create_dict2(level, header):
    if level == 1:
        return _create_dict2_l1(header)
    return _create_dict2_l0(header)


def _create_dict2_l1(header):
    the_dict = dict.fromkeys((
        'Ze',
        'v',
        'width',
        'skewness',
        'kurtosis'))
    if header['dual_polarization'] > 0:
        the_dict.update(dict.fromkeys((
            'ldr',
            'correlation_coefficient',
            'differential_phase')))
    if header['dual_polarization'] == 2:
        the_dict.update(dict.fromkeys((
            'slanted_Ze',
            'slanted_ldr',
            'slanted_correlation_coefficient',
            'specific_differential_phase_shift',
            'differential_attenuation')))
    return the_dict


def _create_dict2_l0(header):
    fix = '' if header['compression'] == 0 else '_compressed'
    the_dict = _init_l0_dict(fix, header)
    if header['compression'] == 2:
        the_dict.update(the_dict.fromkeys((
            'differential_reflectivity_compressed',
            'spectral_correlation_coefficient_compressed',
            'spectral_differential_phase_compressed')))
        if header['dual_polarization'] == 2:
            the_dict.update(the_dict.fromkeys((
                'spectral_slanted_ldr_compressed',
                'spectral_slanted_correlation_coefficient_compressed')))
    return the_dict


def _init_l0_dict(fix, header):
    the_dict = {f"doppler_spectrum{fix}": None}
    if header['dual_polarization'] > 0:
        the_dict.update(the_dict.fromkeys((
            f"doppler_spectrum_h{fix}",
            f"covariance_spectrum_re{fix}",
            f"covariance_spectrum_im{fix}")))
    return the_dict


def _get_float_block_length(level, header, dict1):
    block_length = (len(dict1) + 3 +
                    header['n_temperature_levels'] +
                    (2 * header['n_humidity_levels']) +
                    (2 * header['n_range_levels']))
    if level == 0 and header['dual_polarization'] > 0:
        block_length += 2 * header['n_range_levels']
    return block_length
