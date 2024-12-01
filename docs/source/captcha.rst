.. |br| raw:: html

    <br />


Using Captchas
==============

The **first** login requires a captcha to be solved. Follow-up logins using refresh token do not require a captcha (if login data is persisted).


Getting a captcha token
------------------------

Depending on your region, you will need to solve a different captcha. Please select the appropriate region below.

- `North America <captcha/north_america.html>`_
- `Rest of World <captcha/rest_of_world.html>`_

.. warning::
   The captcha token is only valid for a short time and can only be used once.


Using Home Assistant
--------------------

When using the Home Assistant integration, simply paste the token into the config flow when configuring the account.

Using the CLI
-------------

1. **Generate the Captcha Token**: see `Getting a captcha token <#getting-a-captcha-token>`_. You can generate the token on any device and copy it over. |br| |br|

2. **Login with Captcha Token**: Pass the token via the :code:`--captcha-token` argument when logging in for the first time.

   ::

     bimmerconnected status USERNAME PASSWORD REGION --captcha-token CAPTCHA_TOKEN

3. **Subsequent Logins**: After a successful login, the :code:`--captcha-token` parameter can be omitted until a captcha is required again, indicated by an :code:`invalid login` error.

   ::

     bimmerconnected status USERNAME PASSWORD REGION

.. note::

   Please make sure to use the :code:`--oauth-store` (used by default) to avoid having to solve the captcha again. The user running your automations needs to access this file every time a CLI command is run.

Using the Python API
---------------------

1. **Generate the Captcha Token**: see `Getting a captcha token <#getting-a-captcha-token>`_. You can generate the token on any device and copy it over. |br| |br|

2. **Pass the Captcha Token**: When using the Python API, pass the token via the :code:`hcaptcha_token` argument when creating the account object.

   ::

     account = MyBMWAccount(USERNAME, PASSWORD, REGION, hcaptcha_token=HCAPTCHA_TOKEN)

3. **Subsequent Logins**: Ensure to keep the current :code:`MyBMWAccount` instance in memory to avoid having to solve the captcha again.

  For storing the data across restarts, an example implementation can be found in :code:`bimmerconnected.cli.main()` with 
  :code:`load_oauth_store_from_file()` and :code:`store_oauth_store_to_file()`.

  If you are running this script inside another system (e.g. domoticz), you can also store and read the information using their native tools 
  - it does not have to be a JSON file, as long as the data is stored and read correctly.
