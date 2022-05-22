"""Mock for Connected Drive Backend."""

import json
from pathlib import Path
from typing import Any, Dict, List, Union

from bimmer_connected.api.regions import Regions

RESPONSE_DIR = Path(__file__).parent / "responses"

TEST_USERNAME = "some_user"
TEST_PASSWORD = "my_secret"
TEST_REGION = Regions.REST_OF_WORLD
TEST_REGION_STRING = "rest_of_world"

VIN_F11 = "some_vin_F11"
VIN_F31 = "some_vin_F31"
VIN_F35 = "some_vin_F35"
VIN_F44 = "some_vin_F44"
VIN_F45 = "some_vin_F45"
VIN_F48 = "some_vin_F48"
VIN_G01 = "some_vin_G01"
VIN_G05 = "some_vin_G05"
VIN_G08 = "some_vin_G08"
VIN_G21 = "some_vin_G21"
VIN_G23 = "some_vin_G23"
VIN_G30 = "some_vin_G30"
VIN_I01_NOREX = "some_vin_I01_NOREX"
VIN_I01_REX = "some_vin_I01_REX"

ALL_FINGERPRINTS: List[Dict] = []


def get_fingerprint_count() -> int:
    """Returns number of loaded vehicles."""
    return len(ALL_FINGERPRINTS)


def load_response(path: Union[Path, str]) -> Any:
    """Load a stored response."""
    with open(path, "rb") as file:
        if Path(path).suffix == ".json":
            return json.load(file)
        return file.read().decode("UTF-8")


for fingerprint in RESPONSE_DIR.rglob("vehicles_v2_*_0.json"):
    ALL_FINGERPRINTS.extend(load_response(fingerprint))


def get_deprecation_warning_count(caplog):
    """Return all logged DeprecationWarnings."""
    return [r for r in caplog.records if r.levelname == "WARNING" and "DeprecationWarning" in r.message]


# # VehicleState has different names than the json file. So we need to map some of the
# # parameters.
# ATTRIBUTE_MAPPING = {
#     'remainingFuel': 'remaining_fuel',
#     'position': 'gps_position',
#     'cbsData': 'condition_based_services',
#     'checkControlMessages': 'check_control_messages',
#     'doorLockState': 'door_lock_state',
#     'updateReason': 'last_update_reason',
#     'chargingLevelHv': 'charging_level_hv',
#     'chargingStatus': 'charging_status',
#     'maxRangeElectric': 'max_range_electric',
#     'remainingRangeElectric': 'remaining_range_electric',
#     'parkingLight': 'parking_lights',
#     'remainingRangeFuel': 'remaining_range_fuel',
#     'updateTime': 'timestamp',
#     'chargingTimeRemaining': 'charging_time_remaining'
# }

# # these are additional attributes in the API, not available in the status.json
# ADDITIONAL_ATTRIBUTES = [
#     'remaining_range_total',    # added by bimmer_connected
#     'charging_time_remaining',  # only present while charging
#     'sunroof',                  # not available in all vehicles
#     'lids',                     # required for existing Home Assistant binary sensors
#     'windows',                  # required for existing Home Assistant binary sensors
#     'lights_parking',           # required for existing Home Assistant binary sensors
#     'steering',                 # para not available in all vehicles
# ]

# # there attributes are not (yet) implemented
# MISSING_ATTRIBUTES = [
#     'remainingRangeFuelMls',      # we're not using miles
#     'remainingRangeElectricMls',  # we're not using miles
#     'maxRangeElectricMls',        # we're not using miles
#     'chargingTimeRemaining',      # only present while charging
#     'sunroof',                    # not available in all vehicles
#     'lights_parking',             # required for existing Home Assistant binary sensors
#     'steering',                   # para not available in all vehicles
#     'vehicleCountry',             # para not available in all vehicles
# ]

# AVAILABLE_STATES_MAPPING = {
#     "statisticsAvailable": {True: ["LAST_TRIP", "ALL_TRIPS"]},
#     "chargingControl": {"WEEKLY_PLANNER": ["CHARGING_PROFILE"]},
#     "lastDestinations": {"SUPPORTED": ["DESTINATIONS"]},
#     "rangeMap": {"RANGE_CIRCLE": ["RANGEMAP"]}
# }

# POI_DATA = {
#     "lat": 37.4028943,
#     "lon": -121.9700289,
#     "name": "49ers",
#     "additional_info": "Hi Sam",
#     "street": "4949 Marie P DeBartolo Way",
#     "city": "Santa Clara",
#     "postal_code": "CA 95054",
#     "country": "United States",
#     "website": "https://www.49ers.com/",
#     "phone_numbers": ["+1 408-562-4949"]
# }

# POI_REQUEST = {
#     "min": ("data=%7B%22poi%22%3A+%7B%22lat%22%3A+37.4028943%2C+%22lon%22%3A+-121.9700289"
#             "%2C+%22additionalInfo%22%3A+%22Sent+with+%5Cu2665+by+bimmer_connected%22%7D%7D"),
#     "all": ("data=%7B%22poi%22%3A+%7B%22lat%22%3A+37.4028943%2C+%22lon%22%3A+-121.9700289"
#             "%2C+%22name%22%3A+%2249ers%22%2C+%22additionalInfo%22%3A+%22Hi+Sam%22"
#             "%2C+%22street%22%3A+%224949+Marie+P+DeBartolo+Way%22%2C+%22city%22%3A+%22Santa+Clara%22"
#             "%2C+%22postalCode%22%3A+%22CA+95054%22%2C+%22country%22%3A+%22United+States%22"
#             "%2C+%22website%22%3A+%22https%3A%2F%2Fwww.49ers.com%2F%22"
#             "%2C+%22phoneNumbers%22%3A+%5B%22%2B1+408-562-4949%22%5D%7D%7D")
# }

# MESSAGE_DATA = {"subject": "This is a subject...", "text": "This is a message!"}

# MESSAGE_REQUEST = {
#     "min": ("data=%7B%22poi%22%3A+%7B%22additionalInfo%22%3A+%22This+is+a+message%21%22%7D%7D"),
#     "all": ("data=%7B%22poi%22%3A+%7B%22name%22%3A+%22This+is+a+subject...%22%2C+%22additionalInfo"
#             "%22%3A+%22This+is+a+message%21%22%7D%7D")
# }


# def load_response_json(filename: str) -> dict:
#     """load a stored response from a file"""
#     with open(os.path.join(RESPONSE_DIR, filename), encoding='UTF-8') as json_file:
#         return json.load(json_file)


# class BackendMock:
#     """Mock for Connected Drive Backend."""

#     # pylint: disable=too-many-arguments

#     def __init__(self) -> None:
#         """Constructor."""
#         self.last_request = []
#         self.responses = [
#             MockResponse('https://.+/gcdm/.*/?oauth/authenticate',
#                          headers=_AUTH_RESPONSE_HEADERS,
#                          data_files=['auth/authorization_response.json'],
#                          status_code=200),
#             MockResponse('https://.+/gcdm/.*/?oauth/token',
#                          headers=_AUTH_RESPONSE_HEADERS,
#                          data_files=['auth/auth_token.json'],
#                          status_code=200),
#             MockResponse('https://.+/webapi/v1/user/vehicles$',
#                          data_files=['vehicles.json']),
#         ]

#     def get(self, url: str, headers: dict = None, data: str = None, allow_redirects: bool = None, params=None) \
#             -> 'MockResponse':
#         """Mock for requests.get function."""
#         self.last_request.append(MockRequest(url, headers, data, request_type='GET', allow_redirects=allow_redirects,
#                                              params=params))
#         return self._find_response(url)

#     def post(self, url: str, headers: dict = None, data: str = None, allow_redirects: bool = None, params=None) \
#             -> 'MockResponse':
#         """Mock for requests.post function."""
#         self.last_request.append(MockRequest(url, headers, data, request_type='GET', allow_redirects=allow_redirects,
#                                              params=params))
#         return self._find_response(url)

#     def add_response(self, regex: str, data: str = None, data_files: List[str] = None,
#                      headers: dict = None, status_code=200) -> None:
#         """Add a response to the backend."""
#         self.responses.append(MockResponse(regex, data, data_files, headers, status_code))

#     def _find_response(self, url) -> 'MockResponse':
#         """Find a proper response for a requested url."""
#         for response in self.responses:
#             if response.regex.search(url):
#                 response.step_responses()
#                 return response
#         return MockResponse(regex='', data='unknown url: {}'.format(url), status_code=404)

#     def setup_default_vehicles(self) -> None:
#         """Setup the vehicle configuration in a mock backend."""
#         for vin, path in TEST_VEHICLE_DATA.items():
#             self.add_response('https://.+/webapi/v1/user/vehicles/{vin}/status$'.format(vin=vin),
#                               data_files=['{path}/status.json'.format(path=path)])

#     def Session(self) -> 'BackendMock':  # pylint: disable=invalid-name
#         """Returns itself as a requests.Session style object"""
#         return self


# class MockRequest:  # pylint: disable=too-few-public-methods
#     """Stores the attributes of a request."""

#     # pylint: disable=too-many-arguments

#     def __init__(self, url, headers, data, request_type=None, allow_redirects=None, params=None) -> None:
#         self.url = url
#         self.headers = headers
#         self.headers["Host"] = urllib.parse.urlparse(url).netloc
#         self.data = data
#         self.request_type = request_type
#         self.allow_redirects = allow_redirects
#         self.params = params


# class MockResponse:
#     """Mocks requests.response."""

#     # pylint: disable=too-many-arguments

#     def __init__(self, regex: str, data: str = None, data_files: List[str] = None, headers: dict = None,
#                  status_code: int = 200) -> None:
#         """Constructor."""
#         self.regex = re.compile(regex)
#         self.status_code = status_code
#         self.headers = headers
#         self._usage_count = 0
#         if self.headers is None:
#             self.headers = {}

#         if data_files is not None:
#             self._data = []
#             for data_file in data_files:
#                 with open(os.path.join(RESPONSE_DIR, data_file), encoding='UTF-8') as response:
#                     self._data.append(response.read())
#         else:
#             self._data = [data]

#     def json(self) -> dict:
#         """Parse the text of the response as a jsons string."""
#         return json.loads(self.text)

#     @property
#     def text(self) -> str:
#         """Get the raw data from the response."""
#         return self._data[self._usage_count-1]

#     @property
#     def next(self) -> str:
#         """Get the next url (i.e. forwarded URL) for a response. Only used for authentication."""
#         class AttributeDict(dict):
#             """Simulate attributes from a dict."""
#             __slots__ = ()
#             __getattr__ = dict.__getitem__
#             __setattr__ = dict.__setitem__
#         return AttributeDict(
#             {
#                 "path_url": "/?code=some_login_code&client_id=31c357a0-7a1d-4590-aa99-33b97244d048&nonce=login_nonce"
#             }
#         )

#     def step_responses(self):
#         """Step through the list of responses.

#         The last response will be repeated forever.
#         """
#         self._usage_count = min(len(self._data), self._usage_count+1)
