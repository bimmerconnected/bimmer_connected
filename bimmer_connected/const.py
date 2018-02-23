"""Version numbers of bimmer_connected."""
MAJOR_VERSION = 0
MINOR_VERSION = 4
PATCH_VERSION = '0_dev'

__short_version__ = '{}.{}'.format(MAJOR_VERSION, MINOR_VERSION)
__version__ = '{}.{}'.format(__short_version__, PATCH_VERSION)


"""urls for different services."""

COUNTRY_SELECTION_URL = 'https://www.bmw-connecteddrive.com/cms/default/default/country-selection.json'
AUTH_URL = 'https://customer.bmwgroup.com/gcdm/oauth/authenticate'

REMOTE_SERVICE_URL = '{server}/api/vehicle/remoteservices/v1/{vin}/{service}'
VEHICLE_STATE_URL = '{server}/api/vehicle/dynamic/v1/{vin}'
VEHICLE_SPECS_URL = '{server}/api/vehicle/specs/v1/{vin}'
LIST_VEHICLES_URL = '{server}/api/me/vehicles/v2'
