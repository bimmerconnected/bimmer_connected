:mod:`bimmerconnected` CLI
==========================

The :code:`bimmerconnected` CLI is a command line interface to interact with the BMW ConnectedDrive API. 
A full documentation of the commands can be found below.

.. warning::

   The CLI will store your tokens in a file called :mod:`.bimmer_connected.json` in your home directory (:code:`--oauth-store` parameter).
   You can move this file, but is is required to function properly (have multiple calls). 
   The data is stored in plain text, so protect this file accordingly.

.. note::

   The first login (or after a long time) requires a captcha to be solved (see :doc:`captcha`).
   Follow-up logins using refresh token do not require a captcha (as data is persisted as per above).
   
   These follow-up logins also **do not** require the :code:`--captcha-token` parameter.

:mod:`bimmerconnected`
-----------------------

.. _cli_module:

.. argparse::
   :module: bimmer_connected.cli
   :func: main_parser
   :prog: bimmerconnected
