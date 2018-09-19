"""Mock for Connected Drive Backend."""

import re
import os
import json
from typing import List
from bimmer_connected.country_selector import Regions

RESPONSE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'responses')

TEST_USERNAME = 'some_user'
TEST_PASSWORD = 'my_secret'
TEST_REGION = Regions.REST_OF_WORLD
G31_VIN = 'G31_NBTevo_VIN'
F48_VIN = 'F48_VIN'
I01_VIN = 'I01_VIN'
F15_VIN = 'F15_VIN'
I01_NOREX_VIN = 'I01_NOREX_VIN'
F45_VIN = 'F45_VIN'

#: Mapping of VINs to test data directories
TEST_VEHICLE_DATA = {
    G31_VIN: 'G31_NBTevo',
    F48_VIN: 'F48',
    I01_VIN: 'I01_REX',
    I01_NOREX_VIN: 'I01_NOREX',
    F15_VIN: 'F15',
    F45_VIN: 'F45',
}

_AUTH_RESPONSE_HEADERS = {
    'X-Powered-By': 'JOY',
    'Content-Type': 'application/json',
    'X-CorrelationID': 'Id-cde5a45a0802dd010000000031546948 0',
    'Via': '1.0 lpb2vcn02 (BMW Group API Gateway)',
    'Transfer-Encoding': 'chunked',
    'X-NodeID': '02',
    'Max-Forwards': '20',
    'Date': 'Sun, 11 Mar 2018 08:16:13 GMT',
    'Content-Encoding': 'gzip'}

# VehicleState has different names than the json file. So we need to map some of the
# parameters.
ATTRIBUTE_MAPPING = {
    'remainingFuel': 'remaining_fuel',
    'position': 'gps_position',
    'cbsData': 'condition_based_services',
    'checkControlMessages': 'check_control_messages',
    'doorLockState': 'door_lock_state',
    'updateReason': 'last_update_reason',
    'chargingLevelHv': 'charging_level_hv',
    'chargingStatus': 'charging_status',
    'maxRangeElectric': 'max_range_electric',
    'remainingRangeElectric': 'remaining_range_electric',
    'parkingLight': 'parking_lights',
    'remainingRangeFuel': 'remaining_range_fuel',
    'updateTime': 'timestamp',
    'chargingTimeRemaining': 'charging_time_remaining',
}

# these are additional attributes in the API, not available in the status.json
ADDITIONAL_ATTRIBUTES = [
    'remaining_range_total',    # added by bimmer_connected
    'charging_time_remaining',  # only present while charging
    'sunroof',                  # not available in all vehicles
]

# there attributes are not (yet) implemented
MISSING_ATTRIBUTES = [
    'remainingRangeFuelMls',      # we're not using miles
    'remainingRangeElectricMls',  # we're not using miles
    'maxRangeElectricMls',        # we're not using miles
    'chargingTimeRemaining',      # only present while charging
    'sunroof',                    # not available in all vehicles
]


def load_response_json(filename: str) -> dict:
    """load a stored response from a file"""
    with open(os.path.join(RESPONSE_DIR, filename)) as json_file:
        return json.load(json_file)


class BackendMock:
    """Mock for Connected Drive Backend."""

    # pylint: disable=too-many-arguments

    def __init__(self) -> None:
        """Constructor."""
        self.last_request = []
        self.responses = [
            MockResponse('https://.+/gcdm/oauth/token',
                         headers=_AUTH_RESPONSE_HEADERS,
                         data_files=['G31_NBTevo/auth_response.json'],
                         status_code=200),
            MockResponse('https://.+/webapi/v1/user/vehicles$',
                         data_files=['vehicles.json']),
        ]

    def get(self, url: str, headers: dict = None, data: str = None, allow_redirects: bool = None, params=None) \
            -> 'MockResponse':
        """Mock for requests.get function."""
        self.last_request.append(MockRequest(url, headers, data, request_type='GET', allow_redirects=allow_redirects,
                                             params=params))
        return self._find_response(url)

    def post(self, url: str, headers: dict = None, data: str = None, allow_redirects: bool = None, params=None) \
            -> 'MockResponse':
        """Mock for requests.post function."""
        self.last_request.append(MockRequest(url, headers, data, request_type='GET', allow_redirects=allow_redirects,
                                             params=params))
        return self._find_response(url)

    def add_response(self, regex: str, data: str = None, data_files: List[str] = None,
                     headers: dict = None, status_code=200) -> None:
        """Add a response to the backend."""
        self.responses.append(MockResponse(regex, data, data_files, headers, status_code))

    def _find_response(self, url) -> 'MockResponse':
        """Find a proper response for a requested url."""
        for response in self.responses:
            if response.regex.search(url):
                response.step_responses()
                return response
        return MockResponse(regex='', data='unknown url: {}'.format(url), status_code=404)

    def setup_default_vehicles(self) -> None:
        """Setup the vehicle configuration in a mock backend."""
        for vin, path in TEST_VEHICLE_DATA.items():
            self.add_response('https://.+/webapi/v1/user/vehicles/{vin}/status$'.format(vin=vin),
                              data_files=['{path}/status.json'.format(path=path)])


class MockRequest:  # pylint: disable=too-few-public-methods
    """Stores the attributes of a request."""

    # pylint: disable=too-many-arguments

    def __init__(self, url, headers, data, request_type=None, allow_redirects=None, params=None) -> None:
        self.url = url
        self.headers = headers
        self.data = data
        self.request_type = request_type
        self.allow_redirects = allow_redirects
        self.params = params


class MockResponse:
    """Mocks requests.response."""

    # pylint: disable=too-many-arguments

    def __init__(self, regex: str, data: str = None, data_files: List[str] = None, headers: dict = None,
                 status_code: int = 200) -> None:
        """Constructor."""
        self.regex = re.compile(regex)
        self.status_code = status_code
        self.headers = headers
        self._usage_count = 0
        if self.headers is None:
            self.headers = dict()

        if data_files is not None:
            self._data = []
            for data_file in data_files:
                with open(os.path.join(RESPONSE_DIR, data_file)) as response:
                    self._data.append(response.read())
        else:
            self._data = [data]

    def json(self) -> dict:
        """Parse the text of the response as a jsons string."""
        return json.loads(self.text)

    @property
    def text(self) -> str:
        """Get the raw data from the response."""
        return self._data[self._usage_count-1]

    def step_responses(self):
        """Step through the list of responses.

        The last response will be repeated forever.
        """
        self._usage_count = min(len(self._data), self._usage_count+1)
