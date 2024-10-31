Captcha (North America)
=======================

Login to the :code:`north_america` region requires a captcha to be solved. Submit below form and use the returned token when creating the account object.

::

  account = MyBMWAccount(USERNAME, PASSWORD, Regions.REST_OF_WORLD, hcaptcha_token=HCAPTCHA_TOKEN)

.. note::
   Only the first login requires a captcha to be solved. Follow-up logins using refresh token do not require a captcha.
   This requires the tokens to be stored in a file (see :ref:`cli`) or in the python object itself.

.. raw:: html
   :file: _static/captcha_north_america.html