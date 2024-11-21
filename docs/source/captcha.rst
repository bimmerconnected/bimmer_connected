Using Captchas
==============

The **first** login requires a captcha to be solved. Follow-up logins using refresh token do not require a captcha (if login data is persisted).

.. note::
   The captcha token is only valid for a short time and can only be used once.

Depending on your region, you will need to solve a different captcha. Please select the appropriate region below.

- `North America <captcha/north_america.html>`_
- `Rest of World <captcha/rest_of_world.html>`_

Using the Python API
---------------------

When using the Python API, pass the token via the :code:`hcaptcha_token` argument when creating the account object.

.. warning::

   Ensure to save the current `MyBMWAccount` instance (or at least, the `refresh_token` and `gcid` attributes) to avoid having to solve the captcha again.

::

  account = MyBMWAccount(USERNAME, PASSWORD, REGION, hcaptcha_token=HCAPTCHA_TOKEN)


Using the CLI
-------------
When using the CLI, pass the token via the :code:`--hcaptcha-token` argument (see `CLI documentation <cli.html#named-arguments>`_).

.. warning::

   Please make sure to use the `--oauth-store` (used by default) to avoid having to solve the captcha again.

::

  bimmerconnected status --captcha-token CAPTCHA_TOKEN USERNAME PASSWORD REGION
