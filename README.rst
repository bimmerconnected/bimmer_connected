bimmer_connected
================

This is a simple library to query and control the status of your BMW from
the connected drive portal.

See :code:`bimmerconnected` for usage instruction or the
`API Documentation <http://bimmer-connected.readthedocs.io/en/latest/>`_.

I wrote this library as I want to include it in Home Assistant.


Compatibility
-------------
This works with BMW vehicles with a ConnectedDrive account.
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

    # get the latest version of the library
    pip3 install --upgrade bimmer_connected

    # run the fingerprint function
    bimmerconnected fingerprint <username> <password> <region> <vin>

This will create a set of log files in the "vehicle_fingerprint" folder.
Before sending the data to anyone please **check for any personal data**.
The following attributes should be replaced with default values:
* vin (=Vehicle Identification Number)
* lat and lon (=GPS position)
* licensePlate

Create a new
`issue in bimmer_connected <https://github.com/ChristianKuehnel/bimmer_connected/issues>`_
and
`add the files as attachment <https://help.github.com/articles/file-attachments-on-issues-and-pull-requests/>`_
to the issue.

Please add your model and year to the title of the issue, to make it easier to organize. If you know the "chassis code" of your car, you can include that too. (For example, Googling "2017 BMW X5" will show a Wikipedia article entitled "BMW X5 (F15)". F15 is therefore the chassis code of the car.)


**Note:** We will then use this data as additional test cases. So we will publish
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

Thank you @gerard33, @m1n3rva, @kernelkraut, @robbz23, @lawtancool for your research and contributions!

This library is basically a best-of of other similar solutions I found,
yet none of them provided a ready to use library with a matching interface
to be used in Home Assistant and is available on pypi.

* https://github.com/edent/BMW-i-Remote/blob/master/python/bmw.py
* https://github.com/jupe76/bmwcdapi/blob/master/bmwcdapi.py
* https://github.com/frankjoke/iobroker.bmw

Thank you for your great software!

License
-------
The bimmer_connected library is licensed under the Apache License 2.0.

Disclaimer
----------
This library is not affiliated with or endorsed by BMW Group.
