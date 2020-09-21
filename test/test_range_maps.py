"""Test for RangeMaps"""
import unittest
from unittest import mock
from test import load_response_json
from bimmer_connected.account import ConnectedDriveAccount
from bimmer_connected.state import VehicleState
from bimmer_connected.const import SERVICE_RANGEMAP
from bimmer_connected.range_maps import RangeMapType, RangeMapQuality

I01_TEST_DATA = load_response_json('I01_NOREX/range_maps.json')


class TestState(unittest.TestCase):
    """Test for LastDestinations."""

    # pylint: disable=protected-access

    def test_parse_i01(self):
        """Test if the parsing of the attributes is working."""
        account = mock.MagicMock(ConnectedDriveAccount)
        state = VehicleState(account, None)
        state._attributes[SERVICE_RANGEMAP] = I01_TEST_DATA['rangemap']
        self.assertEqual(RangeMapQuality.AVERAGE, state.range_maps.range_map_quality)
        self.assertEqual(51.123456, state.range_maps.range_map_center.latitude)
        self.assertEqual(-1.2345678, state.range_maps.range_map_center.longitude)
        self.assertEqual(RangeMapType.ECO_PRO_PLUS, state.range_maps.range_maps[0].range_map_type)
        self.assertEqual(51.6991281509399, state.range_maps.range_maps[0].polyline[0].latitude)
        self.assertEqual(-2.00423240661621, state.range_maps.range_maps[0].polyline[0].longitude)
