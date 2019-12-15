"""Tests for ConnectedDriveVehicle."""
import unittest
from unittest import mock
from test import load_response_json, BackendMock, TEST_USERNAME, TEST_PASSWORD, TEST_REGION, \
    G31_VIN, F48_VIN, I01_VIN, I01_NOREX_VIN, F15_VIN, F45_VIN, F31_VIN, TEST_VEHICLE_DATA, \
    ATTRIBUTE_MAPPING, MISSING_ATTRIBUTES, ADDITIONAL_ATTRIBUTES, POI_DATA, POI_REQUEST, \
    MESSAGE_DATA, MESSAGE_REQUEST

from bimmer_connected.vehicle import ConnectedDriveVehicle, DriveTrainType, PointOfInterest, Message
from bimmer_connected.account import ConnectedDriveAccount


_VEHICLES = load_response_json('vehicles.json')['vehicles']
G31_VEHICLE = _VEHICLES[0]


class TestVehicle(unittest.TestCase):
    """Tests for ConnectedDriveVehicle."""

    def test_drive_train(self):
        """Tests around drive_train attribute."""
        vehicle = ConnectedDriveVehicle(None, G31_VEHICLE)
        self.assertEqual(DriveTrainType.CONVENTIONAL, vehicle.drive_train)

    def test_parsing_attributes(self):
        """Test parsing different attributes of the vehicle."""
        backend_mock = BackendMock()
        with mock.patch('bimmer_connected.account.requests', new=backend_mock):
            account = ConnectedDriveAccount(TEST_USERNAME, TEST_PASSWORD, TEST_REGION)

        for vehicle in account.vehicles:
            print(vehicle.name)
            self.assertIsNotNone(vehicle.drive_train)
            self.assertIsNotNone(vehicle.name)
            self.assertIsNotNone(vehicle.has_internal_combustion_engine)
            self.assertIsNotNone(vehicle.has_hv_battery)
            self.assertIsNotNone(vehicle.drive_train_attributes)

    def test_drive_train_attributes(self):
        """Test parsing different attributes of the vehicle."""
        backend_mock = BackendMock()
        with mock.patch('bimmer_connected.account.requests', new=backend_mock):
            account = ConnectedDriveAccount(TEST_USERNAME, TEST_PASSWORD, TEST_REGION)

        for vehicle in account.vehicles:
            self.assertEqual(vehicle.vin in [G31_VIN, F48_VIN, F15_VIN, I01_VIN, F45_VIN, F31_VIN],
                             vehicle.has_internal_combustion_engine)
            self.assertEqual(vehicle.vin in [I01_VIN, I01_NOREX_VIN],
                             vehicle.has_hv_battery)

    def test_parsing_of_lsc_type(self):
        """Test parsing the lsc type field."""
        backend_mock = BackendMock()
        with mock.patch('bimmer_connected.account.requests', new=backend_mock):
            account = ConnectedDriveAccount(TEST_USERNAME, TEST_PASSWORD, TEST_REGION)

        for vehicle in account.vehicles:
            self.assertIsNotNone(vehicle.lsc_type)

    def test_available_attributes(self):
        """Check that available_attributes returns exactly the arguments we have in our test data."""
        backend_mock = BackendMock()
        with mock.patch('bimmer_connected.account.requests', new=backend_mock):
            account = ConnectedDriveAccount(TEST_USERNAME, TEST_PASSWORD, TEST_REGION)

        for vin, dirname in TEST_VEHICLE_DATA.items():
            vehicle = account.get_vehicle(vin)
            print(vehicle.name)
            status_data = load_response_json('{}/status.json'.format(dirname))
            existing_attributes = status_data['vehicleStatus'].keys()
            existing_attributes = sorted([ATTRIBUTE_MAPPING.get(a, a) for a in existing_attributes
                                          if a not in MISSING_ATTRIBUTES])
            expected_attributes = sorted([a for a in vehicle.available_attributes if a not in ADDITIONAL_ATTRIBUTES])
            self.assertListEqual(existing_attributes, expected_attributes)

    def test_parsing_of_poi_min_attributes(self):
        """Check that a PointOfInterest can be constructed using only latitude & longitude."""
        poi = PointOfInterest(POI_DATA["lat"], POI_DATA["lon"])
        msg = Message.from_poi(poi)
        self.assertEqual(msg.as_server_request, POI_REQUEST["min"])

    def test_parsing_of_poi_all_attributes(self):
        """Check that a PointOfInterest can be constructed using all attributes."""
        poi = PointOfInterest(POI_DATA["lat"], POI_DATA["lon"], name=POI_DATA["name"],
                              additionalInfo=POI_DATA["additionalInfo"], street=POI_DATA["street"],
                              city=POI_DATA["city"], postalCode=POI_DATA["postalCode"],
                              country=POI_DATA["country"], website=POI_DATA["website"],
                              phoneNumbers=POI_DATA["phoneNumbers"])
        msg = Message.from_poi(poi)
        self.assertEqual(msg.as_server_request, POI_REQUEST["all"])

    def test_parsing_of_message_min_attributes(self):
        """Check that a Message can be constructed using text."""
        msg = Message.from_text(MESSAGE_DATA["min"]["text"])
        self.assertEqual(msg.as_server_request, MESSAGE_REQUEST["min"])

    def test_parsing_of_message_all_attributes(self):
        """Check that a Message can be constructed using text."""
        msg = Message.from_text(MESSAGE_DATA["all"]["text"], MESSAGE_DATA["all"]["subject"])
        self.assertEqual(msg.as_server_request, MESSAGE_REQUEST["all"])
