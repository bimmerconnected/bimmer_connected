"""Test for VehicleState."""

import unittest
from unittest import mock
import datetime
from test import load_response_json, TEST_COUNTRY, TEST_PASSWORD, TEST_USERNAME, BackendMock, G31_VIN, F32_VIN
from bimmer_connected.account import ConnectedDriveAccount
from bimmer_connected.state import VehicleState, LidState, LockState, UpdateReason, ConditionBasedServiceStatus, \
    ParkingLightState

G31_TEST_DATA = load_response_json('G31_NBTevo/dynamic.json')
NBT_TEST_DATA = load_response_json('unknown_NBT/dynamic.json')
F48_TEST_DATA = load_response_json('F48_EntryNav/dynamic.json')


class TestState(unittest.TestCase):
    """Test for VehicleState."""

    # pylint: disable=protected-access

    def test_parse_g31(self):
        """Test if the parsing of the attributes is working."""
        account = unittest.mock.MagicMock(ConnectedDriveAccount)
        state = VehicleState(account, None)
        state._attributes = G31_TEST_DATA['attributesMap']

        self.assertEqual(2201, state.mileage)
        self.assertEqual('km', state.unit_of_length)

        self.assertEqual(datetime.datetime(2018, 2, 17, 12, 15, 36), state.timestamp)

        self.assertAlmostEqual(-34.4, state.gps_position[0])
        self.assertAlmostEqual(25.26, state.gps_position[1])

        self.assertAlmostEqual(19, state.remaining_fuel)
        self.assertEqual('l', state.unit_of_volume)

        self.assertAlmostEqual(202, state.remaining_range_fuel)

        self.assertEqual(UpdateReason.DOORSTATECHANGED, state.last_update_reason)

        cbs = state.condition_based_services
        self.assertEqual(3, len(cbs))
        self.assertEqual('00001', cbs[0].code)
        self.assertEqual(ConditionBasedServiceStatus.OK, cbs[0].status)
        self.assertEqual(datetime.datetime(year=2020, month=1, day=1), cbs[0].due_date)
        self.assertEqual(28000, cbs[0].due_distance)

        self.assertEqual('00100', cbs[1].code)
        self.assertEqual(ConditionBasedServiceStatus.OK, cbs[1].status)
        self.assertEqual(datetime.datetime(year=2022, month=1, day=1), cbs[1].due_date)
        self.assertEqual(60000, cbs[1].due_distance)

        self.assertFalse(state.are_parking_lights_on)
        self.assertEqual(ParkingLightState.OFF, state.parking_lights)

    def test_parse_nbt(self):
        """Test if the parsing of the attributes is working."""
        account = unittest.mock.MagicMock(ConnectedDriveAccount)
        state = VehicleState(account, None)
        state._attributes = NBT_TEST_DATA['attributesMap']

        self.assertEqual(1234, state.mileage)
        self.assertEqual('km', state.unit_of_length)

        self.assertIsNone(state.timestamp)

        self.assertAlmostEqual(11.111, state.gps_position[0])
        self.assertAlmostEqual(22.222, state.gps_position[1])

        self.assertAlmostEqual(66, state.remaining_fuel)
        self.assertEqual('l', state.unit_of_volume)

        self.assertIsNone(state.remaining_range_fuel)

        self.assertEqual(UpdateReason.ERROR, state.last_update_reason)

        cbs = state.condition_based_services
        self.assertEqual(6, len(cbs))
        self.assertEqual('00001', cbs[0].code)
        self.assertEqual(ConditionBasedServiceStatus.OVERDUE, cbs[0].status)
        self.assertEqual(datetime.datetime(year=2018, month=12, day=1), cbs[0].due_date)
        self.assertEqual(-500, cbs[0].due_distance)

        self.assertEqual('00002', cbs[2].code)
        self.assertEqual(ConditionBasedServiceStatus.PENDING, cbs[2].status)
        self.assertEqual(140, cbs[2].due_distance)

        self.assertIsNone(state.are_parking_lights_on)
        self.assertIsNone(state.parking_lights)

    def test_parse_f48(self):
        """Test if the parsing of the attributes is working."""
        account = unittest.mock.MagicMock(ConnectedDriveAccount)
        state = VehicleState(account, None)
        state._attributes = F48_TEST_DATA['attributesMap']

        self.assertTrue(state.are_parking_lights_on)
        self.assertEqual(ParkingLightState.LEFT, state.parking_lights)

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
            account = ConnectedDriveAccount(TEST_USERNAME, TEST_PASSWORD, TEST_COUNTRY)
            vehicle = account.get_vehicle(G31_VIN)
            with self.assertRaises(IOError):
                vehicle.state.update_data()

            backend_mock.add_response('.*/api/vehicle/dynamic/v1/{vin}'.format(vin=G31_VIN),
                                      data_files=['G31_NBTevo/dynamic.json'])
            vehicle.state.update_data()
            self.assertEqual(2201, vehicle.state.mileage)

    def test_lids(self):
        """Test features around lids."""
        account = unittest.mock.MagicMock(ConnectedDriveAccount)
        state = VehicleState(account, None)
        state._attributes = G31_TEST_DATA['attributesMap']

        for lid in state.lids:
            self.assertEqual(LidState.CLOSED, lid.state)

        self.assertEqual(0, len(list(state.open_lids)))
        self.assertTrue(state.all_lids_closed)

        state._attributes['door_driver_front'] = LidState.OPEN
        self.assertFalse(state.all_lids_closed)

    def test_windows(self):
        """Test features around lids."""
        account = unittest.mock.MagicMock(ConnectedDriveAccount)
        state = VehicleState(account, None)
        state._attributes = G31_TEST_DATA['attributesMap']

        for window in state.windows:
            self.assertEqual(LidState.CLOSED, window.state)

        self.assertEqual(0, len(list(state.open_windows)))
        self.assertTrue(state.all_windows_closed)

        state._attributes['window_driver_front'] = LidState.INTERMEDIATE
        self.assertFalse(state.all_windows_closed)

    def test_door_locks(self):
        """Test the door locks."""
        account = unittest.mock.MagicMock(ConnectedDriveAccount)
        state = VehicleState(account, None)
        state._attributes = G31_TEST_DATA['attributesMap']

        self.assertEqual(LockState.SECURED, state.door_lock_state)

    def test_parsing_attributes(self):
        """Test parsing different attributes of the vehicle.

        Just make sure parsing that no exception is raised.
        """
        backend_mock = BackendMock()
        with mock.patch('bimmer_connected.account.requests', new=backend_mock):
            backend_mock.setup_default_vehicles()
            account = ConnectedDriveAccount(TEST_USERNAME, TEST_PASSWORD, TEST_COUNTRY)
            account.update_vehicle_states()

            for vehicle in account.vehicles:
                print('testing vehicle {}'.format(vehicle.name))
                state = vehicle.state

                self.assertIsNotNone(state.lids)
                self.assertIsNotNone(state.is_vehicle_tracking_enabled)

                if vehicle.vin != F32_VIN:
                    # these values are not available in the F32
                    self.assertIsNotNone(state.door_lock_state)
                    self.assertIsNotNone(state.timestamp)
                    self.assertIsNotNone(state.mileage)
                    self.assertIsNotNone(state.remaining_fuel)
                    self.assertIsNotNone(state.all_windows_closed)

