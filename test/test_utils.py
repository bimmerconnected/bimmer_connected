"""Tests for ConnectedDriveAccount."""
import datetime
import logging
import sys
import unittest
from unittest.mock import MagicMock
from _pytest.monkeypatch import MonkeyPatch


from bimmer_connected.utils import get_class_property_names, parse_datetime, to_json

from . import RESPONSE_DIR, VIN_G21
from .test_account import get_mocked_account


class TestVehicle(unittest.TestCase):
    """Tests for utils."""

    def setUp(self):
        self.monkeypatch = MonkeyPatch()

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
        # Fake datetime.now() first
        faked_now = datetime.datetime.now()
        faked_now = faked_now.replace(hour=21, minute=28, second=59, microsecond=0)
        if sys.version_info < (3, 7):
            faked_now = faked_now.replace(tzinfo=None)
        datetime_mock = MagicMock(wraps=datetime.datetime)
        datetime_mock.now.return_value = faked_now
        self.monkeypatch.setattr(datetime, "datetime", datetime_mock)

        vehicle = get_mocked_account().get_vehicle(VIN_G21)
        with open(RESPONSE_DIR / "G21" / "json_export.json", "rb") as file:
            expected = file.read().decode("UTF-8")
        if sys.version_info < (3, 7):
            expected = expected.replace("+00:00", "")
        self.assertEqual(expected, to_json(vehicle))

    def test_parse_datetime(self):
        """Test datetime parser."""

        dt_with_milliseconds = datetime.datetime(2021, 11, 12, 13, 14, 15, 567000, tzinfo=datetime.timezone.utc)
        dt_without_milliseconds = datetime.datetime(2021, 11, 12, 13, 14, 15, tzinfo=datetime.timezone.utc)

        if sys.version_info < (3, 7):
            dt_with_milliseconds = dt_with_milliseconds.replace(tzinfo=None)
            dt_without_milliseconds = dt_without_milliseconds.replace(tzinfo=None)

        self.assertEqual(dt_with_milliseconds, parse_datetime("2021-11-12T13:14:15.567Z"))

        self.assertEqual(dt_without_milliseconds, parse_datetime("2021-11-12T13:14:15Z"))

        with self.assertLogs(level=logging.ERROR):
            self.assertIsNone(parse_datetime("2021-14-12T13:14:15Z"))
