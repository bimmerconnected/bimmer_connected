"""Test for VehicleState."""

import datetime
import logging
import unittest
import time_machine

from bimmer_connected.account import ConnectedDriveAccount
from bimmer_connected.vehicle_status import LidState, LockState, ConditionBasedServiceStatus, ChargingState

from . import VIN_F11, VIN_F31, VIN_F48, VIN_G08, VIN_G30, VIN_I01_REX
from .test_account import get_mocked_account


class TestState(unittest.TestCase):
    """Test for VehicleState."""

    # pylint: disable=protected-access

    def test_generic(self):
        """Test generic attributes."""
        status = get_mocked_account().get_vehicle(VIN_G30).status

        expected = datetime.datetime(
            year=2021, month=11, day=11, hour=8, minute=58, second=53, tzinfo=datetime.timezone.utc
        )
        self.assertEqual(expected, status.timestamp)

        self.assertEqual(7991, status.mileage[0])
        self.assertEqual("km", status.mileage[1])

        self.assertTupleEqual((12.3456, 34.5678), status.gps_position)
        self.assertAlmostEqual(123, status.gps_heading)

    def test_range_combustion_no_info(self):
        """Test if the parsing of mileage and range is working"""
        status = get_mocked_account().get_vehicle(VIN_F31).status

        self.assertTupleEqual((32, "LITERS"), status.remaining_fuel)
        self.assertIsNone(status.remaining_range_fuel)
        self.assertIsNone(status.fuel_percent)

        self.assertIsNone(status.charging_level_hv)
        self.assertIsNone(status.remaining_range_electric)

        self.assertIsNone(status.remaining_range_total)

    def test_range_combustion(self):
        """Test if the parsing of mileage and range is working"""
        status = get_mocked_account().get_vehicle(VIN_F48).status

        self.assertTupleEqual((19, "LITERS"), status.remaining_fuel)
        self.assertTupleEqual((308, "km"), status.remaining_range_fuel)
        self.assertIsNone(status.fuel_percent)

        self.assertIsNone(status.charging_level_hv)
        self.assertIsNone(status.remaining_range_electric)

        self.assertTupleEqual((308, "km"), status.remaining_range_total)

    def test_range_phev(self):
        """Test if the parsing of mileage and range is working"""
        status = get_mocked_account().get_vehicle(VIN_G30).status

        self.assertTupleEqual((11, "LITERS"), status.remaining_fuel)
        self.assertTupleEqual((107, "km"), status.remaining_range_fuel)
        self.assertAlmostEqual(28, status.fuel_percent)

        self.assertAlmostEqual(41, status.charging_level_hv)
        self.assertTupleEqual((9, "km"), status.remaining_range_electric)

        self.assertTupleEqual((116, "km"), status.remaining_range_total)

        self.assertAlmostEqual(
            status.remaining_range_fuel[0] + status.remaining_range_electric[0], status.remaining_range_total[0]
        )

    def test_range_rex(self):
        """Test if the parsing of mileage and range is working"""
        status = get_mocked_account().get_vehicle(VIN_I01_REX).status

        self.assertTupleEqual((5, "LITERS"), status.remaining_fuel)
        self.assertTupleEqual((64, "km"), status.remaining_range_fuel)
        self.assertIsNone(status.fuel_percent)

        self.assertAlmostEqual(100, status.charging_level_hv)
        self.assertTupleEqual((164, "km"), status.remaining_range_electric)

        self.assertTupleEqual((228, "km"), status.remaining_range_total)

        self.assertAlmostEqual(
            status.remaining_range_fuel[0] + status.remaining_range_electric[0], status.remaining_range_total[0]
        )

    def test_range_electric(self):
        """Test if the parsing of mileage and range is working"""
        status = get_mocked_account().get_vehicle(VIN_G08).status

        self.assertTupleEqual((0, "LITERS"), status.remaining_fuel)
        self.assertIsNone(status.remaining_range_fuel)
        self.assertEqual(0, status.fuel_percent)

        self.assertAlmostEqual(50, status.charging_level_hv)
        self.assertTupleEqual((179, "km"), status.remaining_range_electric)

        self.assertTupleEqual((179, "km"), status.remaining_range_total)

    @time_machine.travel(
        datetime.datetime.now().replace(
            hour=21, minute=28, second=59, microsecond=0, tzinfo=ConnectedDriveAccount.timezone()
        )
    )
    def test_remaining_charging_time(self):
        """Test if the parsing of mileage and range is working"""
        account = get_mocked_account()
        status = account.get_vehicle(VIN_G08).status
        self.assertEqual(6.53, status.charging_time_remaining)

    @time_machine.travel(
        datetime.datetime.now().replace(
            year=2011,
            month=11,
            day=28,
            hour=21,
            minute=28,
            second=59,
            microsecond=0,
            tzinfo=ConnectedDriveAccount.timezone(),
        )
    )
    def test_charging_end_time(self):
        """Test if the parsing of mileage and range is working"""
        account = get_mocked_account()
        status = account.get_vehicle(VIN_G08).status
        self.assertEqual(datetime.datetime(2011, 11, 29, 4, 1), status.charging_end_time)

    def test_condition_based_services(self):
        """Test condition based service messages."""
        status = get_mocked_account().get_vehicle(VIN_G30).status

        cbs = status.condition_based_services
        self.assertEqual(3, len(cbs))
        self.assertEqual(ConditionBasedServiceStatus.OK, cbs[0].state)
        expected_cbs0 = datetime.datetime(year=2022, month=8, day=1, tzinfo=datetime.timezone.utc)
        self.assertEqual(expected_cbs0, cbs[0].due_date)
        self.assertTupleEqual((25000, "KILOMETERS"), cbs[0].due_distance)

        self.assertEqual(ConditionBasedServiceStatus.OK, cbs[1].state)
        expected_cbs1 = datetime.datetime(year=2023, month=8, day=1, tzinfo=datetime.timezone.utc)
        self.assertEqual(expected_cbs1, cbs[1].due_date)
        self.assertIsNone(cbs[1].due_distance)

        self.assertEqual(ConditionBasedServiceStatus.OK, cbs[2].state)
        expected_cbs2 = datetime.datetime(year=2024, month=8, day=1, tzinfo=datetime.timezone.utc)
        self.assertEqual(expected_cbs2, cbs[2].due_date)
        self.assertTupleEqual((60000, "KILOMETERS"), cbs[2].due_distance)

        self.assertTrue(status.are_all_cbs_ok)

    def test_parse_f31_no_position(self):
        """Test parsing of F31 data with position tracking disabled in the vehicle."""
        status = get_mocked_account().get_vehicle(VIN_F31).status

        self.assertIsNone(status.gps_position)
        self.assertIsNone(status.gps_heading)

    def test_parse_f11_no_position_vehicle_active(self):
        """Test parsing of F11 data with vehicle beeing active."""
        status = get_mocked_account().get_vehicle(VIN_F48).status

        # self.assertTrue(status.is_vehicle_tracking_enabled)
        with self.assertLogs(level=logging.WARNING):
            self.assertTrue(status.is_vehicle_active)
            self.assertIsNone(status.gps_position)
            self.assertIsNone(status.gps_heading)

    def test_parse_g08(self):
        """Test if the parsing of the attributes is working."""
        status = get_mocked_account().get_vehicle(VIN_G08).status

        self.assertTupleEqual((179, "km"), status.remaining_range_electric)
        self.assertTupleEqual((179, "km"), status.remaining_range_total)
        self.assertEqual(ChargingState.CHARGING, status.charging_status)
        self.assertEqual(50, status.charging_level_hv)

    # def test_missing_attribute(self):
    #     """Test if error handling is working correctly."""
    #     account = unittest.mock.MagicMock(ConnectedDriveAccount)
    #     state = VehicleState(account, None)
    #     state._attributes[SERVICE_STATUS] = {}
    #     self.assertIsNone(status.mileage)

    def test_lids(self):
        """Test features around lids."""
        status = get_mocked_account().get_vehicle(VIN_G30).status

        self.assertEqual(6, len(list(status.lids)))
        self.assertEqual(3, len(list(status.open_lids)))
        self.assertFalse(status.all_lids_closed)

        status = get_mocked_account().get_vehicle(VIN_G08).status

        for lid in status.lids:
            self.assertEqual(LidState.CLOSED, lid.state)
        self.assertTrue(status.all_lids_closed)
        self.assertEqual(6, len(list(status.lids)))

    def test_windows_g31(self):
        """Test features around windows."""
        status = get_mocked_account().get_vehicle(VIN_G08).status

        for window in status.windows:
            self.assertEqual(LidState.CLOSED, window.state)

        self.assertEqual(5, len(list(status.windows)))
        self.assertEqual(0, len(list(status.open_windows)))
        self.assertTrue(status.all_windows_closed)

    def test_door_locks(self):
        """Test the door locks."""
        status = get_mocked_account().get_vehicle(VIN_G08).status

        self.assertEqual(LockState.LOCKED, status.door_lock_state)

        status = get_mocked_account().get_vehicle(VIN_I01_REX).status

        self.assertEqual(LockState.UNLOCKED, status.door_lock_state)

    def test_empty_status(self):
        """Test an empy status."""
        status = get_mocked_account().get_vehicle(VIN_F31).status
        status.properties.pop("inMotion")

        with self.assertLogs(level=logging.DEBUG):
            self.assertIsNone(status.is_vehicle_active)

        status.properties = None
        status.status = None

        with self.assertRaises(ValueError):
            self.assertIsNone(status.is_vehicle_active)

    # def test_parsing_attributes(self):
    #     """Test parsing different attributes of the vehicle.

    #     Just make sure parsing that no exception is raised and we get not-None values.
    #     """
    #     backend_mock = BackendMock()
    #     # list of attributes that are ignored at the moment
    #     ignored_attributes = [ATTRIBUTE_MAPPING.get(a, a) for a in MISSING_ATTRIBUTES]
    #     with mock.patch('bimmer_connected.account.requests', new=backend_mock):
    #         backend_mock.setup_default_vehicles()
    #         account = ConnectedDriveAccount(TEST_USERNAME, TEST_PASSWORD, TEST_REGION)
    #         account.update_vehicle_states()

    #         for vehicle in account.vehicles:
    #             print(vehicle.name)
    #             for attribute in (a for a in vehicle.available_attributes if a not in ignored_attributes):
    #                 self.assertIsNotNone(getattr(vehicle.status, attribute), attribute)

    def test_check_control_messages(self):
        """Test handling of check control messages.

        G21 is the only vehicle with active Check Control Messages, so we only expect to get something there.
        However we have no vehicle with issues in check control.
        """
        vehicle = get_mocked_account().get_vehicle(VIN_F11)
        self.assertTrue(vehicle.status.has_check_control_messages)

        ccms = vehicle.status.check_control_messages
        self.assertEqual(2, len(ccms))

        self.assertEqual("Medium", ccms[0].state)
        self.assertEqual("229", ccms[0].ccm_id)
        self.assertEqual(
            (
                "Charge by driving for longer periods or use external charger. "
                "Functions requiring battery will be switched off."
            ),
            ccms[0].description_long,
        )
        self.assertEqual("Battery discharged: Start engine", ccms[0].description_short)

        self.assertEqual("Low", ccms[1].state)
        self.assertEqual("50", ccms[1].ccm_id)
        self.assertEqual(
            (
                "System unable to monitor tire pressure. Check tire pressures manually. "
                "Continued driving possible. Consult service center."
            ),
            ccms[1].description_long,
        )
        self.assertEqual("Flat Tire Monitor (FTM) inactive", ccms[1].description_short)
