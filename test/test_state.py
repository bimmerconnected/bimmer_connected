"""Test for VehicleState."""

import unittest
from unittest import mock
import datetime
from test import load_response_json, TEST_REGION, TEST_PASSWORD, TEST_USERNAME, BackendMock, G31_VIN, \
    ATTRIBUTE_MAPPING, MISSING_ATTRIBUTES
from bimmer_connected.account import ConnectedDriveAccount
from bimmer_connected.state import VehicleState, LidState, LockState, ConditionBasedServiceStatus, \
    ParkingLightState, ChargingState

G31_TEST_DATA = load_response_json('G31_NBTevo/status.json')
G31_NO_POSITION_TEST_DATA = load_response_json('G31_NBTevo/status_position_disabled.json')
F48_TEST_DATA = load_response_json('F48/status.json')
I01_TEST_DATA = load_response_json('I01_REX/status.json')


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

        self.assertTrue(state.is_vehicle_tracking_enabled)
        self.assertAlmostEqual(50.5050, state.gps_position[0])
        self.assertAlmostEqual(10.1010, state.gps_position[1])

        self.assertAlmostEqual(33, state.remaining_fuel)

        self.assertAlmostEqual(321, state.remaining_range_fuel)
        self.assertAlmostEqual(state.remaining_range_fuel, state.remaining_range_total)

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

    def test_parse_g31_no_psoition(self):
        """Test parsing of G31 data with position tracking disabled in the vehicle."""
        account = unittest.mock.MagicMock(ConnectedDriveAccount)
        state = VehicleState(account, None)
        state._attributes = G31_NO_POSITION_TEST_DATA['vehicleStatus']

        self.assertFalse(state.is_vehicle_tracking_enabled)
        self.assertIsNone(state.gps_position)

    def test_parse_f48(self):
        """Test if the parsing of the attributes is working."""
        account = unittest.mock.MagicMock(ConnectedDriveAccount)
        state = VehicleState(account, None)
        state._attributes = F48_TEST_DATA['vehicleStatus']

        self.assertEqual(21529, state.mileage)

        zone = datetime.timezone(datetime.timedelta(0, 3600))
        self.assertEqual(datetime.datetime(year=2018, month=3, day=10, hour=19, minute=35, second=30, tzinfo=zone),
                         state.timestamp)

        self.assertTrue(state.is_vehicle_tracking_enabled)
        self.assertAlmostEqual(50.505050, state.gps_position[0])
        self.assertAlmostEqual(10.1010101, state.gps_position[1])

        self.assertAlmostEqual(39, state.remaining_fuel)

        self.assertAlmostEqual(590, state.remaining_range_fuel)

        self.assertEqual('DOOR_STATE_CHANGED', state.last_update_reason)

        cbs = state.condition_based_services
        self.assertEqual(3, len(cbs))
        self.assertEqual(ConditionBasedServiceStatus.OK, cbs[0].state)
        self.assertEqual(datetime.datetime(year=2019, month=7, day=1), cbs[0].due_date)
        self.assertEqual(9000, cbs[0].due_distance)

        self.assertEqual(ConditionBasedServiceStatus.OK, cbs[1].state)
        self.assertEqual(datetime.datetime(year=2021, month=7, day=1), cbs[1].due_date)
        self.assertEqual(39000, cbs[1].due_distance)

        self.assertTrue(state.are_all_cbs_ok)

        self.assertFalse(state.are_parking_lights_on)
        self.assertEqual(ParkingLightState.OFF, state.parking_lights)

    def test_parse_i01(self):
        """Test if the parsing of the attributes is working."""
        account = unittest.mock.MagicMock(ConnectedDriveAccount)
        state = VehicleState(account, None)
        state._attributes = I01_TEST_DATA['vehicleStatus']

        self.assertEqual(48, state.remaining_range_electric)
        self.assertEqual(154, state.remaining_range_total)
        self.assertEqual(94, state.max_range_electric)
        self.assertEqual(ChargingState.CHARGING, state.charging_status)
        self.assertEqual(datetime.timedelta(minutes=332), state.charging_time_remaining)
        self.assertEqual(54, state.charging_level_hv)

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

        self.assertEqual(6, len(list(state.lids)))
        self.assertEqual(0, len(list(state.open_lids)))
        self.assertTrue(state.all_lids_closed)

        state._attributes['doorDriverFront'] = LidState.OPEN
        self.assertFalse(state.all_lids_closed)

    def test_windows_g31(self):
        """Test features around lids."""
        account = unittest.mock.MagicMock(ConnectedDriveAccount)
        state = VehicleState(account, None)
        state._attributes = G31_TEST_DATA['vehicleStatus']

        for window in state.windows:
            self.assertEqual(LidState.CLOSED, window.state)

        self.assertEqual(5, len(list(state.windows)))
        self.assertEqual(0, len(list(state.open_windows)))
        self.assertTrue(state.all_windows_closed)

        state._attributes['windowDriverFront'] = LidState.INTERMEDIATE
        self.assertFalse(state.all_windows_closed)

    def test_windows_g48(self):
        """Test features around lids."""
        account = unittest.mock.MagicMock(ConnectedDriveAccount)
        state = VehicleState(account, None)
        state._attributes = F48_TEST_DATA['vehicleStatus']

        for window in state.windows:
            self.assertEqual(LidState.CLOSED, window.state)

        self.assertEqual(4, len(list(state.windows)))

    def test_door_locks(self):
        """Test the door locks."""
        account = unittest.mock.MagicMock(ConnectedDriveAccount)
        state = VehicleState(account, None)
        state._attributes = G31_TEST_DATA['vehicleStatus']

        self.assertEqual(LockState.SECURED, state.door_lock_state)

    def test_parsing_attributes(self):
        """Test parsing different attributes of the vehicle.

        Just make sure parsing that no exception is raised and we get not-None values.
        """
        backend_mock = BackendMock()
        # list of attributes that are ignored at the moment
        ignored_attributes = [ATTRIBUTE_MAPPING.get(a, a) for a in MISSING_ATTRIBUTES]
        with mock.patch('bimmer_connected.account.requests', new=backend_mock):
            backend_mock.setup_default_vehicles()
            account = ConnectedDriveAccount(TEST_USERNAME, TEST_PASSWORD, TEST_REGION)
            account.update_vehicle_states()

            for vehicle in account.vehicles:
                print(vehicle.name)
                for attribute in (a for a in vehicle.available_attributes if a not in ignored_attributes):
                    self.assertIsNotNone(getattr(vehicle.state, attribute), attribute)
