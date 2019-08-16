""" BMW ConnectedDrive exception class."""

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

class BMWConnectedDriveException(Exception):
    """ BMW ConnectedDrive API Exception class."""
    def __init__(self, code, *args, **kwargs):
        self.message = ""
        super().__init__(*args, **kwargs)
        self.code = code
        if self.code == 401:
            self.message = 'UNAUTHORIZED'
        elif self.code == 404:
            self.message = 'NOT_FOUND'
        elif self.code == 405:
            self.message = 'MOBILE_ACCESS_DISABLED'
        elif self.code == 408:
            self.message = 'VEHICLE_UNAVAILABLE'
        elif self.code == 423:
            self.message = 'ACCOUNT_LOCKED'
        elif self.code == 429:
            self.message = 'TOO_MANY_REQUESTS'
        elif self.code == 500:
            self.message = 'SERVER_ERROR'
        elif self.code == 503:
            self.message = 'SERVICE_MAINTENANCE'
        elif self.code > 299:
            self.message = "UNKNOWN_ERROR"
