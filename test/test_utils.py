"""Tests for ConnectedDriveAccount."""
import logging
import sys
import unittest
from datetime import datetime, timezone

from bimmer_connected.utils import get_class_property_names, parse_datetime, to_json

from . import RESPONSE_DIR, VIN_G21
from .test_account import get_mocked_account


class TestVehicle(unittest.TestCase):
    """Tests for utils."""

    def test_drive_train(self):
        """Tests available attribute."""
        vehicle = get_mocked_account().get_vehicle(VIN_G21)
        self.assertEqual(
            [
                "available_attributes",
                "available_state_services",
                "brand",
                "charging_profile",
                "drive_train",
                "drive_train_attributes",
                "has_hv_battery",
                "has_internal_combustion_engine",
                "has_range_extender",
                "has_weekly_planner_service",
                "lsc_type",
                "name",
                "to_json",
            ],
            get_class_property_names(vehicle),
        )

    def test_to_json(self):
        """Test serialization to JSON."""
        vehicle = get_mocked_account().get_vehicle(VIN_G21)
        with open(RESPONSE_DIR / "G21" / "json_export.json", "rb") as file:
            expected = file.read().decode("UTF-8")
        self.assertEqual(expected, to_json(vehicle))

    def test_parse_datetime(self):
        """Test datetime parser."""

        dt_with_milliseconds = datetime(2021, 11, 12, 13, 14, 15, 567000, tzinfo=timezone.utc)
        dt_without_milliseconds = datetime(2021, 11, 12, 13, 14, 15, tzinfo=timezone.utc)

        if sys.version_info <= (3, 6):
            dt_with_milliseconds.tzinfo = None
            dt_without_milliseconds.tzinfo = None

        self.assertEqual(dt_with_milliseconds, parse_datetime("2021-11-12T13:14:15.567Z"))

        self.assertEqual(dt_without_milliseconds, parse_datetime("2021-11-12T13:14:15Z"))

        with self.assertLogs(level=logging.ERROR):
            self.assertIsNone(parse_datetime("2021-14-12T13:14:15Z"))
