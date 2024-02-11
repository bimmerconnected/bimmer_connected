Using fingerprints in Home Assistant
====================================
Sometimes it can be useful to load the **fingerprints** used for our **pytest suite** in the development of the Home Assistant component.
This enables debugging of the UI in Home Assistant which is not possible from pytest alone.

.. warning::
  If not already done, `set up the Home Assistant development environment <https://developers.home-assistant.io/docs/development_environment>`_.

Now start Home Assistant at least once and let all python packages install (``hass -c ./config``).
If not already done, set up the **BMW Connected Drive Integration** in Home Assistant.
Shut down Homeassistant afterwards.

Now, we have to "hack" our mocked backend calls into Home Assistant.

.. note::
  Doing so will remove your own account!

Edit ``homeassistant/components/bmw_connected_drive/coordinator.py`` and locate the function ``_async_update_data``. We now have to replace ``await self.account.get_vehicles()``. The ``try .. except`` block should look like this:

.. code-block:: python

  ...
          try:
              from bimmer_connected.tests.conftest import MyBMWMockRouter, ALL_STATES, ALL_CHARGING_SETTINGS
              with MyBMWMockRouter(["WBY00000000REXI01"], ALL_STATES, ALL_CHARGING_SETTINGS):
                  await self.account.get_vehicles()
          except:
  ...

.. note::
  As the first parameter, you can specify a list of VINs for debugging or leave it empty (``None`` or ``[]``) to load all vehicles of our test suite.
