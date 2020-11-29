"""Test for LastDestinations"""
import unittest
from unittest import mock
from test import load_response_json
from bimmer_connected.account import ConnectedDriveAccount
from bimmer_connected.state import VehicleState
from bimmer_connected.const import SERVICE_DESTINATIONS
from bimmer_connected.last_destinations import DestinationType

I01_TEST_DATA = load_response_json('I01_NOREX/last_destinations.json')


class TestState(unittest.TestCase):
    """Test for LastDestinations."""

    # pylint: disable=protected-access

    def test_parse_i01(self):
        """Test if the parsing of the attributes is working."""
        account = mock.MagicMock(ConnectedDriveAccount)
        state = VehicleState(account, None)
        state._attributes[SERVICE_DESTINATIONS] = I01_TEST_DATA['destinations']
        self.assertEqual(DestinationType.DESTINATION, state.last_destinations.last_destinations[0].destination_type)
        self.assertEqual(51.53053283691406, state.last_destinations.last_destinations[0].latitude)
        self.assertEqual(-0.08362331241369247, state.last_destinations.last_destinations[0].longitude)
        self.assertEqual('UNITED KINGDOM', state.last_destinations.last_destinations[0].country)
        self.assertEqual('LONDON', state.last_destinations.last_destinations[0].city)
        self.assertEqual('PITFIELD STREET', state.last_destinations.last_destinations[0].street)
        self.assertEqual('2015-09-25T08:06:11+0200', state.last_destinations.last_destinations[0].created_at)

    def test_available_attributes(self):
        """Check available_attributes for last_destination service."""
        account = mock.MagicMock(ConnectedDriveAccount)
        state = VehicleState(account, None)
        expected_attributes = ['last_destinations']
        existing_attributes = state.last_destinations.available_attributes
        self.assertListEqual(existing_attributes, expected_attributes)
