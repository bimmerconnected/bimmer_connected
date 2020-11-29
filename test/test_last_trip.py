"""Test for LastTrip"""
import unittest
from unittest import mock
from test import load_response_json
from bimmer_connected.account import ConnectedDriveAccount
from bimmer_connected.state import VehicleState
from bimmer_connected.const import SERVICE_LAST_TRIP

I01_TEST_DATA = load_response_json('I01_NOREX/last_trip.json')


class TestState(unittest.TestCase):
    """Test for LastTrip."""

    # pylint: disable=protected-access

    def test_parse_i01(self):
        """Test if the parsing of the attributes is working."""
        account = mock.MagicMock(ConnectedDriveAccount)
        state = VehicleState(account, None)
        state._attributes[SERVICE_LAST_TRIP] = I01_TEST_DATA['lastTrip']
        self.assertEqual(0.53, state.last_trip.efficiencyValue)
        self.assertEqual(141, state.last_trip.total_distance)
        self.assertEqual(100.1, state.last_trip.electric_distance)
        self.assertEqual(16.6, state.last_trip.average_electric_consumption)
        self.assertEqual(2, state.last_trip.average_recuperation)
        self.assertEqual(0, state.last_trip.driving_mode_value)
        self.assertEqual(0.39, state.last_trip.acceleration_value)
        self.assertEqual(0.81, state.last_trip.anticipation_value)
        self.assertEqual(0.79, state.last_trip.total_consumption_value)
        self.assertEqual(0.66, state.last_trip.auxiliary_consumption_value)
        self.assertEqual(1.9, state.last_trip.average_combined_consumption)
        self.assertEqual(71, state.last_trip.electric_distance_ratio)
        self.assertEqual(0, state.last_trip.saved_fuel)
        self.assertEqual('2015-12-01T20:44:00+0100', state.last_trip.date)
        self.assertEqual(124, state.last_trip.duration)

    def test_available_attributes(self):
        """Check available_attributes for last_trip service."""
        account = mock.MagicMock(ConnectedDriveAccount)
        state = VehicleState(account, None)
        expected_attributes = ['acceleration_value', 'anticipation_value', 'auxiliary_consumption_value',
                               'average_combined_consumption', 'average_electric_consumption', 'average_recuperation',
                               'date', 'driving_mode_value', 'duration', 'efficiency_value', 'electric_distance',
                               'electric_distance_ratio', 'saved_fuel', 'total_consumption_value', 'total_distance']
        existing_attributes = state.last_trip.available_attributes
        self.assertListEqual(existing_attributes, expected_attributes)
