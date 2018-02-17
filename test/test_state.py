"""Test for VehicleState."""

import unittest
from unittest import mock
import datetime
from test import load_response_json
from bimmer_connected import ConnectedDriveAccount
from bimmer_connected.state import VehicleState

TEST_DATA = load_response_json('G31_NBTevo/dynamic.json')


class TestState(unittest.TestCase):
    """Test for VehicleState."""

    # pylint: disable=protected-access

    def test_parse(self):
        """Test if the parsing of the attributes is working."""
        account = unittest.mock.MagicMock(ConnectedDriveAccount)
        state = VehicleState(account, None)
        state._attributes = TEST_DATA['attributesMap']

        self.assertEqual(2201, state.mileage)
        self.assertEqual('km', state.unit_of_length)

        self.assertEqual(datetime.datetime(2018, 2, 17, 12, 15, 36), state.timestamp)

        self.assertAlmostEqual(-34.4, state.gps_position[0])
        self.assertAlmostEqual(25.26, state.gps_position[1])

        self.assertAlmostEqual(19, state.remaining_fuel)
        self.assertEqual('l', state.unit_of_volume)

        self.assertAlmostEqual(202, state.remaining_range_fuel)

    def test_missing_attribute(self):
        """Test if error handling is working correctly."""
        account = unittest.mock.MagicMock(ConnectedDriveAccount)
        state = VehicleState(account, None)
        state._attributes = dict()
        with self.assertRaises(ValueError):
            state.mileage  # pylint: disable = pointless-statement

    @mock.patch('bimmer_connected.vehicle.VehicleState.update_data')
    def test_no_attributes(self, _):
        """Test if error handling is working correctly."""
        account = unittest.mock.MagicMock(ConnectedDriveAccount)
        state = VehicleState(account, None)
        with self.assertRaises(ValueError):
            state.mileage  # pylint: disable = pointless-statement
