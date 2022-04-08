"""Tests for ConnectedDriveAccount."""
import datetime
import logging
import os
import time
import unittest
from unittest.mock import Mock

import time_machine

from bimmer_connected.country_selector import get_region_from_name, valid_regions
from bimmer_connected.utils import get_class_property_names, parse_datetime, to_json

from . import RESPONSE_DIR, VIN_G21
from .test_account import get_mocked_account


class TestUtils(unittest.TestCase):
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
                "is_vehicle_tracking_enabled",
                "lsc_type",
                "name",
            ],
            get_class_property_names(vehicle),
        )

    @time_machine.travel("2011-11-28 21:28:59 +0000", tick=False)
    def test_to_json(self):
        """Test serialization to JSON."""
        # Force UTC
        os.environ["TZ"] = "UTC"
        time.tzset()

        account = get_mocked_account()
        account.timezone = Mock(return_value=datetime.timezone.utc)
        vehicle = account.get_vehicle(VIN_G21)

        # Unset UTC after vehicle has been loaded
        del os.environ["TZ"]
        time.tzset()

        with open(RESPONSE_DIR / "G21" / "json_export.json", "rb") as file:
            expected = file.read().decode("UTF-8")
        self.assertEqual(expected, to_json(vehicle, indent=4))

    def test_parse_datetime(self):
        """Test datetime parser."""

        dt_with_milliseconds = datetime.datetime(2021, 11, 12, 13, 14, 15, 567000, tzinfo=datetime.timezone.utc)
        dt_without_milliseconds = datetime.datetime(2021, 11, 12, 13, 14, 15, tzinfo=datetime.timezone.utc)

        self.assertEqual(dt_with_milliseconds, parse_datetime("2021-11-12T13:14:15.567Z"))

        self.assertEqual(dt_without_milliseconds, parse_datetime("2021-11-12T13:14:15Z"))

        with self.assertLogs(level=logging.ERROR):
            self.assertIsNone(parse_datetime("2021-14-12T13:14:15Z"))


class TestCountrySelector(unittest.TestCase):
    """Tests for Country Selector."""

    def test_valid_regions(self):
        """Test valid regions."""
        self.assertListEqual(["north_america", "china", "rest_of_world"], valid_regions())

    def test_unknown_region(self):
        """Test unkown region."""
        with self.assertRaises(ValueError):
            get_region_from_name("unkown")
