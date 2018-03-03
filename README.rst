bimmer_connected
================

This is a simple library to query and control the status of your BMW from
the connected drive portal.

See status.py and remote_light_flash.py for usage instruction or the
`API Documentation <http://bimmer-connected.readthedocs.io/en/latest/>`_.

I wrote this library as I want to include it in Home Assistant.


Compatibility
-------------
So far it is tested on vehicles with a 'NBTEvo', 'EntryEvo', 'NBT', or 'EntryNav' navigation system. 
If you have any trouble with other navigation systems, please create an issue
with your server responses (see next section).


Data Contributions
------------------

If some features do not work for your vehicle, we would need the data
returned form the server to analyse this and potentially extend the code.
Different models and head unit generations lead to different responses from
the server.

If you want to contribute your data, perform the following steps:

::

    git clone https://github.com/ChristianKuehnel/bimmer_connected.git
    cd bimmer_connected
    ./generate_vehicle_fingerprint.py <username> <password> <country>

This will create a set of log files in the "vehicle_fingerprint" folder.
Before sending the data to anyone please **remove any personal data** from it:

* Replace your vehicle identification number (VIN) with something else like "my_vin"
* Replace the location of your vehicle (gps_lat, gps_lng) with some generig numbers e.g. 11.111
* Remove the SMSESSION and token attributes from \*_header.json

We will then use this data as additional test cases. So we will publish
(parts of) it (after checking for personal information again) and use
this as test cases for our library. If you do not want this, please
let us know in advance.

Code Contributions
------------------
Contributions are welcome! Please make sure that your code passed the "tox" checks.
And please add tests where it makes sense. The more the better.

.. image:: https://travis-ci.org/ChristianKuehnel/bimmer_connected.svg?branch=master
    :target: https://travis-ci.org/ChristianKuehnel/bimmer_connected
.. image:: https://coveralls.io/repos/github/ChristianKuehnel/bimmer_connected/badge.svg?branch=master
    :target: https://coveralls.io/github/ChristianKuehnel/bimmer_connected?branch=master

Thank you
---------

This library is basically a best-of of other similar solutions I found,
yet none of them provided a ready to use library with a matching interface
for Home Assistant interface and released it on pypi...

* https://github.com/edent/BMW-i-Remote/blob/master/python/bmw.py
* https://github.com/jupe76/bmwcdapi/blob/master/bmwcdapi.py
* https://github.com/frankjoke/iobroker.bmw

Thank you for your great software!

Disclaimer
----------
This library is not affiliated with or endorsed by BMW Group.
