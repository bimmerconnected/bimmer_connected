bimmer_connected
================

.. image:: https://badge.fury.io/py/bimmer-connected.svg
    :target: https://pypi.org/project/bimmer-connected
.. image:: https://pepy.tech/badge/bimmer-connected/week
    :target: https://pepy.tech/project/bimmer-connected/week
.. image:: https://pepy.tech/badge/bimmer-connected/month
    :target: https://pepy.tech/project/bimmer-connected/month
.. image:: https://pepy.tech/badge/bimmer-connected
    :target: https://pepy.tech/project/bimmer-connected
.. image:: https://github.com/bimmerconnected/bimmer_connected/actions/workflows/test.yml/badge.svg?branch=master
    :target: https://github.com/bimmerconnected/bimmer_connected/actions/workflows/test.yml?query=branch%3Amaster
.. image:: https://readthedocs.org/projects/bimmer-connected/badge/?version=latest
    :target: https://bimmer-connected.readthedocs.io/en/latest/?badge=latest
.. image:: https://codecov.io/gh/bimmerconnected/bimmer_connected/branch/master/graph/badge.svg?token=qNT50j82f6
    :target: https://codecov.io/gh/bimmerconnected/bimmer_connected
    

This is a simple library to query and control the status of your BMW or Mini vehicle from
the MyBMW portal.


Installation
============
:code:`bimmer_connected` requires **Python 3.6 or above**. Just install the latest release from `PyPI <https://pypi.org/project/bimmer-connected/>`_ 
using :code:`pip3 install --upgrade bimmer_connected`. 

Alteratively, clone the project and execute :code:`pip install -e .` to install the current 
:code:`master` branch.

Usage
=====
While this library is mainly written to be included in `Home Assistant <https://www.home-assistant.io/integrations/bmw_connected_drive/>`_, it can be use on its own.

After installation, execute :code:`bimmerconnected` from command line for usage instruction
or see the full `CLI documentation <http://bimmer-connected.readthedocs.io/en/latest/#cli>`_.

Please be aware that :code:`bimmer_connected` is an :code:`async` library when using it in Python code.
The description of the :code:`modules` can be found in the `module documentation 
<http://bimmer-connected.readthedocs.io/en/latest/#module>`_.

Example in an :code:`asyncio` event loop
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
::

    import asyncio
    from bimmer_connected.account import MyBMWAccount
    from bimmer_connected.api.regions import Regions

    async def main():
        account = MyBMWAccount(USERNAME, PASSWORD, Regions.REST_OF_WORLD)
        await account.get_vehicles()
        vehicle = account.get_vehicle(VIN)
        print(vehicle.brand, vehicle.name, vehicle.vin)
        
        result = await vehicle.remote_services.trigger_remote_light_flash()
        print(result.state)

    asyncio.run(main())

    
Example in non-async code
^^^^^^^^^^^^^^^^^^^^^^^^^^

::

    import asyncio
    from bimmer_connected.account import MyBMWAccount
    from bimmer_connected.api.regions import Regions


    account = MyBMWAccount(USERNAME, PASSWORD, Regions.REST_OF_WORLD)
    asyncio.run(account.get_vehicles())
    vehicle = account.get_vehicle(VIN)
    print(vehicle.brand, vehicle.name, vehicle.vin)
        
    result = asyncio.run(vehicle.remote_services.trigger_remote_light_flash())
    print(result.state)


Compatibility
=============
This works with BMW (and Mini) vehicles with a MyBMW account.
So far it is tested on vehicles with a 'MGU', 'NBTEvo', 'EntryEvo', 'NBT', or 'EntryNav'
navigation system. If you have any trouble with other navigation systems, please create 
an issue with your server responses (see next section).

To use this library, your BMW (or Mini) must have the remote services enabled for your vehicle. 
You might need to book this in the MyBMW/Mini Connected portal and this might cost 
some money. In addition to that you need to enable the Remote Services in your infotainment 
system in the vehicle.

Different models of vehicles and infotainment systems result in different types of attributes
provided by the server. So the experience with the library will certainly vary across the different 
vehicle models.

Data Contributions
==================
If some features do not work for your vehicle, we would need the data
returned form the server to analyse this and potentially extend the code.
Different models and head unit generations lead to different responses from
the server.

If you want to contribute your data, perform the following steps:

::

    # get the latest version of the library
    pip3 install --upgrade bimmer_connected

    # run the fingerprint function
    bimmerconnected fingerprint <username> <password> <region>

This will create a set of log files in the "vehicle_fingerprint" folder.
Before sending the data to anyone please **check for any personal data** such as **dealer name** or **country**. 

The following attributes are by default replaced with anonymized values:

* :code:`vin` (Vehicle Identification Number)
* :code:`lat` and :code:`lon` (GPS position)
* :code:`licensePlate`
* :code:`information of dealer`

Create a new
`fingerprint data contribution <https://github.com/bimmerconnected/bimmer_connected/discussions/new?category_id=32000818>`_
and add the files as attachment to the discussion.

Please add your model and year to the title of the issue, to make it easier to organize. 
If you know the "chassis code" of your car, you can include that too. (For example, 
googling "2017 BMW X5" will show a Wikipedia article entitled "BMW X5 (F15)". F15 is 
therefore the chassis code of the car.)


**Note:** We will then use this data as additional test cases. So we will publish
(parts of) it (after checking for personal information again) and use
this as test cases for our library. If you do not want this, please
let us know in advance.

Code Contributions
==================
Contributions are welcome! Please make sure that your code passes the checks in :code:`.github/workflows/test.yml`. 
We currently test against :code:`flake8`, :code:`pylint` and our own :code:`pytest` suite.
And please add tests where it makes sense. The more the better.

See the `contributing guidelines <https://github.com/bimmerconnected/bimmer_connected/blob/master/CONTRIBUTING.md>`_ for more details.

Thank you
=========

Thank you to all `contributors <https://github.com/bimmerconnected/bimmer_connected/graphs/contributors>`_ for your research and contributions! And thanks to everyone who shares the `fingerprint data <https://github.com/bimmerconnected/bimmer_connected#data-contributions>`_ of their vehicles which we use to test the code.
A special thanks to @HuChundong, @muxiachuixue, @vividmuse for figuring out how to solve login issues!

This library is basically a best-of of other similar solutions,
yet none of them provided a ready to use library with a matching interface
to be used in Home Assistant and is available on pypi.

* https://github.com/edent/BMW-i-Remote
* https://github.com/jupe76/bmwcdapi
* https://github.com/frankjoke/iobroker.bmw
* https://github.com/TA2k/ioBroker.bmw
* https://gitee.com/ichuixue/bmw_shortcuts / https://www.icloud.com/shortcuts/eb064e89e6b647d2828a404227b91c4a

Thank you for your great software!

License
=======
The bimmer_connected library is licensed under the Apache License 2.0.

Disclaimer
==========
This library is not affiliated with or endorsed by BMW Group.
