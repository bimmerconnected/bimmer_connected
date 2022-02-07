Using fingerprints in Home Assistant
====================================
Sometimes it can be useful to load the **fingerprints** used for our **pytest suite** in the development of the Home Assistant component. 

Set up bimmer_connected
-----------------------
Clone the repository to ``~/bimmer_connected``:

.. code-block:: bash

   git clone https://github.com/bimmerconnected/bimmer_connected.git ~/bimmer_connected

.. note::
  
  Make sure that you can access this path from inside your Home Assistant virtual environment!

Edit the  ``_get_vehicles()`` function in `account.py#L370-L392 <https://github.com/bimmerconnected/bimmer_connected/blob/master/bimmer_connected/account.py#L370-L392>`_
and add the following code between ``self._get_oauth_token()`` and ``for brand in CarBrand:``:

.. code-block:: python

   from pathlib import Path
   files = (Path().home() / "bimmer_connected" / "test" / "responses").rglob("vehicles_v2_*_0.json")
   for file in files:
     for vehicle_dict in json.load(open(file, 'r')):
       # If vehicle already exists, just update it's state
       existing_vehicle = self.get_vehicle(vehicle_dict["vin"])
       if existing_vehicle:
         existing_vehicle.update_state(vehicle_dict)
       else:
         self._vehicles.append(MyBMWVehicle(self, vehicle_dict))

Set up Home Assistant
---------------------
If not already done, `set up the Home Assistant development environment <https://developers.home-assistant.io/docs/development_environment>`_.

Now start Home Assistant at least once and let all python packages install (``hass -c ./config``). 
If not already done, set up the **BMW Connected Drive Integration** in Home Assistant. 
Shut down Homeassistant afterwards.

In the Home Assistant virtual environment, install the freshly adjusted version of ``bimmer_connected``:

.. code-block:: bash

  pip3 install -e ~/bimmer_connected

Start Home Assistant using ``hass -c ./config --skip-pip`` and see all cars we have fingerprints of + your own cars.

.. warning::
   If ``--skip-pip`` is omitted when starting Home Assistant, the version of ``bimmer_connected`` defined in 
   ``homeassistant/components/bmw_connected_drive/manifest.json`` will be loaded and the Home Assistant last two steps have to be executed again.

