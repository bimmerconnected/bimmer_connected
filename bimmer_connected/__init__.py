"""Library to read data from the BMW Connected Drive portal.

The library bimmer_connected provides a Python interface to interact
with the BMW Connected Drive web service. It allows you to read
the current state of the vehicle and also trigger remote services.

Disclaimer:
This library is not affiliated with or endorsed by BMW Group.
"""

import pkg_resources  # part of setuptools

__version__ = pkg_resources.get_distribution("bimmer_connected").version
