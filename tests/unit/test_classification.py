import numpy as np
from numpy.testing import assert_array_equal, assert_array_almost_equal
from collections import namedtuple
import pytest

CATEGORIZE_BITS = namedtuple('CATEGORIZE_BITS', ['category_bits', 'quality_bits'])

CATEGORIZE_BITS(category_bits={'droplet': np.asarray([[1, 0, 1, 0, 0, 0],
                                                     [0, 1, 1, 0, 0, 0]], dtype=bool),
                               'falling': np.asarray([[1, 0, 1, 0, 0, 0],
                                                      [0, 1, 1, 0, 0, 0]], dtype=bool),
                               'cold': np.asarray([[1, 0, 1, 0, 0, 0],
                                                  [0, 1, 1, 0, 0, 0]], dtype=bool),
                               'melting': np.asarray([[1, 0, 1, 0, 0, 0],
                                                     [0, 1, 1, 0, 0, 0]], dtype=bool),
                               'aerosols': np.asarray([[1, 0, 1, 0, 0, 0],
                                                      [0, 1, 1, 0, 0, 0]], dtype=bool),
                               'insects': np.asarray([[1, 0, 1, 0, 0, 0],
                                                     [0, 1, 1, 0, 0, 0]], dtype=bool),
                               },
                quality_bits={'radar': np.asarray([[1, 0, 1, 0, 0, 0],
                                                  [0, 1, 1, 0, 0, 0]], dtype=bool),
                              'lidar': np.asarray([[1, 0, 1, 0, 0, 0],
                                                   [0, 1, 1, 0, 0, 0]], dtype=bool),
                              'clutter': np.asarray([[1, 0, 1, 0, 0, 0],
                                                    [0, 1, 1, 0, 0, 0]], dtype=bool),
                              'molecular': np.asarray([[1, 0, 1, 0, 0, 0],
                                                      [0, 1, 1, 0, 0, 0]], dtype=bool),
                              'attenuated': np.asarray([[1, 0, 1, 0, 0, 0],
                                                       [0, 1, 1, 0, 0, 0]], dtype=bool),
                              'corrected': np.asarray([[1, 0, 1, 0, 0, 0],
                                                      [0, 1, 1, 0, 0, 0]], dtype=bool)})


def test_get_target_classification():
    assert True


def test_get_detection_status():
    assert True
