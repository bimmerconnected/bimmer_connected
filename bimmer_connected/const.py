"""URLs for different services and error code mapping."""

AUTH_URL = 'https://customer.bmwgroup.com/{gcdm_oauth_endpoint}/authenticate'
AUTH_URL_LEGACY = 'https://{server}/gcdm/oauth/token'
BASE_URL = 'https://{server}/webapi/v1'

VEHICLES_URL = BASE_URL + '/user/vehicles'
VEHICLE_VIN_URL = VEHICLES_URL + '/{vin}'
VEHICLE_STATUS_URL = VEHICLE_VIN_URL + '/status'
REMOTE_SERVICE_STATUS_URL = VEHICLE_VIN_URL + '/serviceExecutionStatus?serviceType={service_type}'
REMOTE_SERVICE_URL = VEHICLE_VIN_URL + "/executeService"
VEHICLE_IMAGE_URL = VEHICLE_VIN_URL + "/image?width={width}&height={height}&view={view}"
VEHICLE_POI_URL = VEHICLE_VIN_URL + '/sendpoi'

# Possible error codes, other codes are mapped to UNKNOWN_ERROR
ERROR_CODE_MAPPING = {
    401: 'UNAUTHORIZED',
    404: 'NOT_FOUND',
    405: 'MOBILE_ACCESS_DISABLED',
    408: 'VEHICLE_UNAVAILABLE',
    423: 'ACCOUNT_LOCKED',
    429: 'TOO_MANY_REQUESTS',
    500: 'SERVER_ERROR',
    503: 'SERVICE_MAINTENANCE',
}
