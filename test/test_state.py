"""Test for VehicleState."""

import unittest
from unittest import mock
import datetime
from test import load_response_json, TEST_REGION, TEST_PASSWORD, TEST_USERNAME, BackendMock, G31_VIN
from bimmer_connected.account import ConnectedDriveAccount
from bimmer_connected.state import VehicleState, LidState, LockState, ConditionBasedServiceStatus, \
    ParkingLightState

G31_TEST_DATA = load_response_json('G31_NBTevo/status.json')


class TestState(unittest.TestCase):
    """Test for VehicleState."""

    # pylint: disable=protected-access

    def test_parse_g31(self):
        """Test if the parsing of the attributes is working."""
        account = unittest.mock.MagicMock(ConnectedDriveAccount)
        state = VehicleState(account, None)
        state._attributes = G31_TEST_DATA['vehicleStatus']

        self.assertEqual(4126, state.mileage)

        zone = datetime.timezone(datetime.timedelta(0, 3600))
        self.assertEqual(datetime.datetime(year=2018, month=3, day=10, hour=11, minute=39, second=41, tzinfo=zone),
                         state.timestamp)

        self.assertAlmostEqual(50.5050, state.gps_position[0])
        self.assertAlmostEqual(10.1010, state.gps_position[1])

        self.assertAlmostEqual(33, state.remaining_fuel)

        self.assertAlmostEqual(321, state.remaining_range_fuel)

        self.assertEqual('VEHICLE_SHUTDOWN', state.last_update_reason)

        cbs = state.condition_based_services
        self.assertEqual(3, len(cbs))
        self.assertEqual(ConditionBasedServiceStatus.OK, cbs[0].state)
        self.assertEqual(datetime.datetime(year=2020, month=1, day=1), cbs[0].due_date)
        self.assertEqual(25000, cbs[0].due_distance)

        self.assertEqual(ConditionBasedServiceStatus.OK, cbs[1].state)
        self.assertEqual(datetime.datetime(year=2022, month=1, day=1), cbs[1].due_date)
        self.assertEqual(60000, cbs[1].due_distance)

        self.assertTrue(state.are_all_cbs_ok)

        self.assertFalse(state.are_parking_lights_on)
        self.assertEqual(ParkingLightState.OFF, state.parking_lights)

    def test_parse_timeformat(self):
        """Test parsing of the time string."""
        date = "2018-03-10T11:39:41+0100"
        zone = datetime.timezone(datetime.timedelta(0, 3600))
        self.assertEqual(datetime.datetime(year=2018, month=3, day=10, hour=11, minute=39, second=41, tzinfo=zone),
                         VehicleState._parse_datetime(date))

    def test_missing_attribute(self):
        """Test if error handling is working correctly."""
        account = unittest.mock.MagicMock(ConnectedDriveAccount)
        state = VehicleState(account, None)
        state._attributes = dict()
        self.assertIsNone(state.mileage)

    @mock.patch('bimmer_connected.vehicle.VehicleState.update_data')
    def test_no_attributes(self, _):
        """Test if error handling is working correctly."""
        account = unittest.mock.MagicMock(ConnectedDriveAccount)
        state = VehicleState(account, None)
        with self.assertRaises(ValueError):
            state.mileage  # pylint: disable = pointless-statement

    def test_update_data(self):
        """Test update_data method."""
        backend_mock = BackendMock()
        with mock.patch('bimmer_connected.account.requests', new=backend_mock):
            account = ConnectedDriveAccount(TEST_USERNAME, TEST_PASSWORD, TEST_REGION)
            vehicle = account.get_vehicle(G31_VIN)
            with self.assertRaises(IOError):
                vehicle.state.update_data()

            backend_mock.setup_default_vehicles()

            vehicle.state.update_data()
            self.assertEqual(4126, vehicle.state.mileage)

    def test_lids(self):
        """Test features around lids."""
        account = unittest.mock.MagicMock(ConnectedDriveAccount)
        state = VehicleState(account, None)
        state._attributes = G31_TEST_DATA['vehicleStatus']

        for lid in state.lids:
            self.assertEqual(LidState.CLOSED, lid.state)

        self.assertEqual(0, len(list(state.open_lids)))
        self.assertTrue(state.all_lids_closed)

        state._attributes['doorDriverFront'] = LidState.OPEN
        self.assertFalse(state.all_lids_closed)

    def test_windows(self):
        """Test features around lids."""
        account = unittest.mock.MagicMock(ConnectedDriveAccount)
        state = VehicleState(account, None)
        state._attributes = G31_TEST_DATA['vehicleStatus']

        for window in state.windows:
            self.assertEqual(LidState.CLOSED, window.state)

        self.assertEqual(0, len(list(state.open_windows)))
        self.assertTrue(state.all_windows_closed)

        state._attributes['windowDriverFront'] = LidState.INTERMEDIATE
        self.assertFalse(state.all_windows_closed)

    def test_door_locks(self):
        """Test the door locks."""
        account = unittest.mock.MagicMock(ConnectedDriveAccount)
        state = VehicleState(account, None)
        state._attributes = G31_TEST_DATA['vehicleStatus']

        self.assertEqual(LockState.SECURED, state.door_lock_state)

    def test_parsing_attributes(self):
        """Test parsing different attributes of the vehicle.

        Just make sure parsing that no exception is raised.
        """
        backend_mock = BackendMock()
        with mock.patch('bimmer_connected.account.requests', new=backend_mock):
            backend_mock.setup_default_vehicles()
            account = ConnectedDriveAccount(TEST_USERNAME, TEST_PASSWORD, TEST_REGION)
            account.update_vehicle_states()

            for vehicle in account.vehicles:
                print('testing vehicle {}'.format(vehicle.name))
                state = vehicle.state

                self.assertIsNotNone(state.lids)
                self.assertIsNotNone(state.is_vehicle_tracking_enabled)
                self.assertIsNotNone(state.windows)
                self.assertIsNotNone(state.condition_based_services)

                self.assertIsNotNone(state.door_lock_state)
                self.assertIsNotNone(state.timestamp)
                self.assertIsNotNone(state.mileage)
                self.assertIsNotNone(state.remaining_fuel)
                self.assertIsNotNone(state.all_windows_closed)
