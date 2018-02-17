# bimmer_connected
This is a simple library to query and control the status of your BMW from
the connected drive portal.

See status.py and remote_light_flash.py for usage instruction or the
`API Documentation <http://bimmer-connected.readthedocs.io/en/latest/>`_.

I wrote this library as I want to include it in Home Assistant.


# Compatibility
So far it is only tested with one vehicle with a "NBTEvo" navigation system. 
If you have any trouble with other navigation systems, please create an issue.

Also: If you need additional attributes parsed from the answer from the server,
please create and issue.

# Thank you
This library is basically a best-of of other similar solutions I found,
yet none of them priovided a ready to use library with a machting interface
for Home Assistant interface and released it on pypi...

* https://github.com/edent/BMW-i-Remote/blob/master/python/bmw.py
* https://github.com/jupe76/bmwcdapi/blob/master/bmwcdapi.py
* https://github.com/frankjoke/iobroker.bmw

Thank you for our great software!

# Contributions
Contributions are welcome!
Please make sure that your code passed the `tox` checks.

And please add tests where it makes sense. The more the better.

[![Build Status](https://travis-ci.org/ChristianKuehnel/bimmer_connected.svg?branch=master)](https://travis-ci.org/ChristianKuehnel/bimmer_connected)
[![Coverage Status](https://coveralls.io/repos/github/ChristianKuehnel/bimmer_connected/badge.svg?branch=master)](https://coveralls.io/github/ChristianKuehnel/bimmer_connected?branch=master)


# Disclaimer
This library is not affiliated with or endorsed by BMW Group.