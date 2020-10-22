"""Test for Efficiency"""
import unittest
from unittest import mock
from test import load_response_json
from bimmer_connected.account import ConnectedDriveAccount
from bimmer_connected.state import VehicleState
from bimmer_connected.const import SERVICE_EFFICIENCY

G30_PHEV_OS7_TEST_DATA = load_response_json('G30_PHEV_OS7/efficiency.json')


class TestState(unittest.TestCase):
    """Test for Efficiency."""

    # pylint: disable=protected-access

    def test_parse_g30_phev_os7(self):
        """Test if the parsing of the attributes is working."""
        account = mock.MagicMock(ConnectedDriveAccount)
        state = VehicleState(account, None)
        state._attributes[SERVICE_EFFICIENCY] = G30_PHEV_OS7_TEST_DATA
        self.assertEqual('PHEV', state.efficiency.model_type)
        self.assertEqual(0, state.efficiency.efficiency_quotient)
        self.assertEqual('LASTTRIP_DELTA_KM', state.efficiency.last_trip_list[0].name)
        self.assertEqual('KM', state.efficiency.last_trip_list[0].unit)
        self.assertEqual('--', state.efficiency.last_trip_list[0].last_trip)
        self.assertEqual('TIMESTAMP_STATISTICS_RESET', state.efficiency.life_time_list[2].name)
        self.assertIsNone(state.efficiency.life_time_list[2].unit)
        self.assertEqual('12.01.2020', state.efficiency.life_time_list[2].life_time)
        self.assertEqual('DRIVING_MODE', state.efficiency.characteristic_list[1].characteristic)
        self.assertEqual(0, state.efficiency.characteristic_list[1].quantity)
