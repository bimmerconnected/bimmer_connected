"""Library to read data from the BMW Connected Drive portal.

The library bimmer_connected provides a Python interface to interact
with the BMW Connected Drive web service. It allows you to read
the current state of the vehicle and also trigger remote services.

Disclaimer:
This library is not affiliated with or endorsed by BMW Group.
"""

import sys

if sys.version_info >= (3, 8):
    from importlib.metadata import version
else:
    from importlib_metadata import version

__version__ = version("bimmer_connected")
