"""Mock for Connected Drive Backend."""

import re
import os
import json
from typing import List

RESPONSE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'responses')

TEST_USERNAME = 'some_user'
TEST_PASSWORD = 'my_secret'
TEST_COUNTRY = 'Germany'
G31_VIN = 'G31_NBTEvo_VIN'
F48_VIN = 'F48_EntryNav_VIN'
F32_VIN = 'F32_NBTevo_VIN'
I03_VIN = 'I01_NBT_VIN'

#: Mapping of VINs to test data directories
TEST_VEHICLE_DATA = {
    G31_VIN: 'G31_NBTevo',
    F48_VIN: 'F48_EntryNav',
    F32_VIN: 'F32_NBTevo',
    I03_VIN: 'I01_NBT',
}

_AUTH_RESPONSE_HEADERS = {
    'X-c2b-request-id': 'SOME_ID',
    'Location': 'https://www.bmw-connecteddrive.com/app/default/static/external-dispatch.html#'
                'state=SOME_STATE_STRING&access_token=SOME_TOKEN_STRING&token_type=Bearer&'
                'expires_in=7199',
    'X-Powered-By': 'JOY',
    'X-c2b-timestamp': '1518874356235',
    'Transfer-Encoding': 'chunked',
    'Keep-Alive': 'timeout=5, max=100',
    'Access-Control-Allow-Headers': 'Authorization, Origin, X-c2b-Authorization, X-c2b-mTAN, '
                                    'X-Requested-With, X-c2b-Sender-Id, Content-Type, Accept, '
                                    'Cache-Control, KeyId',
    'X-NodeID': '01',
    'Content-Type': 'text/html; charset="utf-8"', 'Max-Forwards': '20',
    'Date': 'Sat, 17 Feb 2018 13:32:35 GMT',
    'Access-Control-Allow-Methods': 'POST, GET, OPTIONS, PUT, DELETE, HEAD',
    'Server': 'Apache',
    'Via': '1.0 lpb2vcn01 (BMW Group API Gateway)',
    'Access-Control-Allow-Credentials': 'true',
    'X-CorrelationID': 'Id-ANOTHER_ID 0',
    'Set-Cookie': 'SMSESSION=SOME_SESSION_KEY;Domain=customer.bmwgroup.com;Path=/;secure',
    'Content-Encoding': 'gzip', 'Connection': 'Keep-Alive'}


def load_response_json(filename: str) -> dict:
    """load a stored response from a file"""
    with open(os.path.join(RESPONSE_DIR, filename)) as json_file:
        return json.load(json_file)


class BackendMock(object):
    """Mock for Connected Drive Backend."""

    # pylint: disable=too-many-arguments

    def __init__(self) -> None:
        """Constructor."""
        self.last_request = None
        self.responses = [
            MockResponse('https://customer.bmwgroup.com/gcdm/oauth/authenticate',
                         headers=_AUTH_RESPONSE_HEADERS,
                         status_code=302),
            MockResponse('.*/api/me/vehicles/v2',
                         data_files=['vehicles.json']),
        ]

    def get(self, url: str, headers: dict = None, data: str = None, allow_redirects: bool = None) -> 'MockResponse':
        """Mock for requests.get function."""
        self.last_request = MockRequest(url, headers, data, request_type='GET', allow_redirects=allow_redirects)
        return self._find_response(url)

    def post(self, url: str, headers: dict = None, data: str = None, allow_redirects: bool = None) -> 'MockResponse':
        """Mock for requests.post function."""
        self.last_request = MockRequest(url, headers, data, request_type='GET', allow_redirects=allow_redirects)
        return self._find_response(url)

    def add_response(self, regex: str, data: str = None, data_files: List[str] = None,
                     headers: dict = None, status_code=200) -> None:
        """Add a response to the backend."""
        self.responses.append(MockResponse(regex, data, data_files, headers, status_code))

    def _find_response(self, url) -> 'MockResponse':
        """Find a proper response for a requested url."""
        for response in self.responses:
            if response.regex.search(url):
                return response
        return MockResponse(regex='', data='unknown url: {}'.format(url), status_code=404)

    def setup_default_vehicles(self) -> None:
        """Setup the vehicle configuration in a mock backend."""
        for vin, path in TEST_VEHICLE_DATA.items():
            self.add_response('.*/api/vehicle/dynamic/v1/{vin}'.format(vin=vin),
                              data_files=['{}/dynamic.json'.format(path)])

            self.add_response('.*/api/vehicle/specs/v1/{vin}'.format(vin=vin),
                              data_files=['{}/specs.json'.format(path)])


class MockRequest(object):  # pylint: disable=too-few-public-methods
    """Stores the attributes of a request."""

    # pylint: disable=too-many-arguments

    def __init__(self, url, headers, data, request_type=None, allow_redirects=None) -> None:
        self.url = url
        self.headers = headers
        self.data = data
        self.request_type = request_type
        self.allow_redirects = allow_redirects


class MockResponse(object):
    """Mocks requests.response."""

    # pylint: disable=too-many-arguments

    def __init__(self, regex: str, data: str = None, data_files: List[str] = None, headers: dict = None,
                 status_code: int = 200) -> None:
        """Constructor."""
        self.regex = re.compile(regex)
        self.status_code = status_code
        self.headers = headers
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
        return self._data.pop(0)
