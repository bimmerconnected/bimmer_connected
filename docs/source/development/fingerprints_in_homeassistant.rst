Using fingerprints in Home Assistant
====================================
Sometimes it can be useful to load the **fingerprints** used for our **pytest suite** in the development of the Home Assistant component.
This enables debugging of the UI in Home Assistant which is not possible from pytest alone.

.. warning::
  This is for the `Home Assistant development environment <https://developers.home-assistant.io/docs/development_environment>`_ only! Do not do this on your live instance!

Setup and start Home Assistant in the `development environment <https://developers.home-assistant.io/docs/development_environment>`_ at least once and let all python packages install (``hass -c ./config``).
If not already done, set up the **BMW Connected Drive Integration**. You need to login a MyBMW account at least once. Shut down Homeassistant afterwards.

.. note::
  The MyBMW account does not need to contain vehicles, a demo account without attached vehicles is sufficient.

Now, we have to "hack" our mocked backend calls into Home Assistant.

Edit ``homeassistant/components/bmw_connected_drive/coordinator.py`` and locate the function ``def _async_update_data()``. We now have to replace ``await self.account.get_vehicles()``. The ``try .. except`` block should look like this:

.. code-block:: python

  ...
          try:
              from bimmer_connected.tests.conftest import MyBMWMockRouter, ALL_STATES, ALL_CHARGING_SETTINGS, ALL_PROFILES
              with MyBMWMockRouter(["WBA00000000DEMO02","WBA00000000DEMO03"], ALL_PROFILES, ALL_STATES, ALL_CHARGING_SETTINGS):
                  await self.account.get_vehicles()
          except:
  ...

As the first parameter, you can specify a list of VINs for debugging or leave it empty (``None`` or ``[]``) to load all vehicles of our test suite.
