"""Test for AllTrips."""
import unittest
from unittest import mock
from test import load_response_json
from bimmer_connected.account import ConnectedDriveAccount
from bimmer_connected.state import VehicleState
from bimmer_connected.const import SERVICE_ALL_TRIPS

I01_TEST_DATA = load_response_json('I01_NOREX/all_trips.json')


class TestState(unittest.TestCase):
    """Test for VehicleState."""

    # pylint: disable=protected-access

    def test_parse_i01(self):
        """Test if the parsing of the attributes is working."""
        account = mock.MagicMock(ConnectedDriveAccount)
        state = VehicleState(account, None)
        state._attributes[SERVICE_ALL_TRIPS] = I01_TEST_DATA['allTrips']
        self.assertEqual('1970-01-01T01:00:00+0100', state.all_trips.reset_date)
        self.assertEqual(35820, state.all_trips.battery_size_max)
        self.assertEqual(87.58, state.all_trips.saved_co2)
        self.assertEqual(515.177, state.all_trips.saved_co2_green_energy)
        self.assertEqual(0, state.all_trips.total_saved_fuel)

        self.assertEqual(0, state.all_trips.average_electric_consumption.community_low)
        self.assertEqual(16.33, state.all_trips.average_electric_consumption.community_average)
        self.assertEqual(35.53, state.all_trips.average_electric_consumption.community_high)
        self.assertEqual(14.76, state.all_trips.average_electric_consumption.user_average)

        self.assertEqual(0, state.all_trips.average_recuperation.community_low)
        self.assertEqual(3.76, state.all_trips.average_recuperation.community_average)
        self.assertEqual(14.03, state.all_trips.average_recuperation.community_high)
        self.assertEqual(2.3, state.all_trips.average_recuperation.user_average)

        self.assertEqual(121.58, state.all_trips.chargecycle_range.community_average)
        self.assertEqual(200, state.all_trips.chargecycle_range.community_high)
        self.assertEqual(72.62, state.all_trips.chargecycle_range.user_average)
        self.assertEqual(135, state.all_trips.chargecycle_range.user_high)
        self.assertEqual(60, state.all_trips.chargecycle_range.user_current_charge_cycle)

        self.assertEqual(1, state.all_trips.total_electric_distance.community_low)
        self.assertEqual(12293.65, state.all_trips.total_electric_distance.community_average)
        self.assertEqual(77533.6, state.all_trips.total_electric_distance.community_high)
        self.assertEqual(3158.66, state.all_trips.total_electric_distance.user_total)

        self.assertEqual(0, state.all_trips.average_combined_consumption.community_low)
        self.assertEqual(1.21, state.all_trips.average_combined_consumption.community_average)
        self.assertEqual(6.2, state.all_trips.average_combined_consumption.community_high)
        self.assertEqual(0.36, state.all_trips.average_combined_consumption.user_average)

    def test_available_attributes(self):
        """Check available_attributes for all_trips service."""
        account = mock.MagicMock(ConnectedDriveAccount)
        state = VehicleState(account, None)
        expected_attributes = ['average_combined_consumption', 'average_electric_consumption',
                               'average_recuperation', 'battery_size_max', 'chargecycle_range',
                               'reset_date', 'saved_co2', 'saved_co2_green_energy',
                               'total_electric_distance', 'total_saved_fuel']
        existing_attributes = state.all_trips.available_attributes
        self.assertListEqual(existing_attributes, expected_attributes)
