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

   Ensure to save the current :code:`MyBMWAccount` instance (or at least, the :code:`refresh_token` and :code:`gcid` attributes) to avoid having to solve the captcha again.

::

  account = MyBMWAccount(USERNAME, PASSWORD, REGION, hcaptcha_token=HCAPTCHA_TOKEN)


Using the CLI
-------------
When using the CLI, pass the token via the :code:`--captcha-token` argument (see `CLI documentation <cli.html#named-arguments>`_).

.. warning::

   Please make sure to use the :code:`--oauth-store` (used by default) to avoid having to solve the captcha again.

::

  bimmerconnected status --captcha-token CAPTCHA_TOKEN USERNAME PASSWORD REGION

After a successful login, the :code:`--captcha-token` parameter can be omitted (until a captcha is required again, indicated by a :code:`invalid login` error).

::

  bimmerconnected status USERNAME PASSWORD REGION


