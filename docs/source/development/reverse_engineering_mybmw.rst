Reverse engineering the MyBMW API
=================================

This document should be seen as a help in setting up a working environment to intercept traffic of the MyBMW app.
Not every step will be described fully, this guide is rather a summary and list for further reading.
It will most likely need adjustments to your specific setup.

The MyBMW app is built with the Flutter framework and needs some additional persuasion to reveal the traffic.

Disclaimer
----------

Note that we are actively disabling important security measures such as SSL/TLS encryption to understand which commands and messages are shared between the MyBMW app and the MyBMW servers.

Also note that there could always be changes to the API or the app itself made by BMW to stop us from understanding what is going on.

Acknowledgement
---------------
Most of this document would not exist without the amazing work of Jeroen Becker:

* `Intercepting traffic from Android Flutter applications (ARMv7) <https://blog.nviso.eu/2019/08/13/intercepting-traffic-from-android-flutter-applications/>`_
* `Intercepting Flutter traffic on Android (ARMv8) <https://blog.nviso.eu/2020/05/20/intercepting-flutter-traffic-on-android-x64/>`_
* `Intercepting Flutter traffic on iOS <https://blog.nviso.eu/2020/06/12/intercepting-flutter-traffic-on-ios/>`_

Software & hardware requirements
--------------------------------

.. note::
   This document is based on the MyBMW **Android** app. It should work similarly using **iPhones**. If possible, please create a PR with more details.

You will need:

* A proxy with MITM capabilities such as `mitmproxy <https://mitmproxy.org/>`_
* A **rooted** android phone with a version supported by MyBMW (currently Android 6.0 Marshmallow).
  It could also work using an `Android emulator <https://developer.android.com/studio/run/emulator>`_.
* Access to your phone using ADB (via USB)
* `ProxyDroid <https://play.google.com/store/apps/details?id=org.proxydroid>`_ to forward all traffic to your proxy
* `Ghidra <https://ghidra-sre.org/>`_ to find the location to patch out SSL verification
* A python environment with `frida <https://frida.re/>`_
* `frida-android-helper <https://github.com/Hamz-a/frida-android-helper>`_ to help installing ``frida`` on your phone

Finding the location of SSL verification
----------------------------------------

The following steps are required if the location of the SSL verification function is not known.
If it is, please continue with the `next section <#preparations-on-phone>`_.
For more details, please refer to `Jeroen Becker's work <#acknowledgement>`_.

Get an APK/XAPK of the MyBMW app (from your phone or one of the many download sites). APK names include:

* ``de.bmw.connected.mobile20.cn`` (china)
* ``de.bmw.connected.mobile20.na`` (north america)
* ``de.bmw.connected.mobile20.row`` (rest of world)

Now extract ``config.arm64-v8a.apk`` or ``config.armeabi-v7a.apk`` from the APK package (depending of your phone's target architecture).

In Ghidra, load and analyze ``lib/ARCH/libflutter.so``.

After analyze has finished, go to ``Search`` > ``For Scalar`` and search for value ``390``. Find ``mov r3, #0x186`` and jump to it.

Double click on function name on right side to get the hex address and first bytes of the function

.. code::

  Example: 2d e9 f0 4f a3 b0 81 46 50 20 10 70

Preparations on phone
---------------------

On your phone, add your custom CA certificates to the system store (`instructions for emulator <https://docs.mitmproxy.org/stable/howto-install-system-trusted-ca-android/>`_,
but works on **rooted** devies in similar fashion). This is required as the login screen is using the default Android WebView component,
which again behaves differently from Flutter (or rather, behaves like expected).

Add your local proxy server to your Android system using ProxyDroid.


Disabling SSL verification with frida
-------------------------------------
Install & upgrade ``frida-tools`` & ``frida-android-helper`` (see `requirements <#software-hardware-requirements>`_).
Make sure that both are on the latest version.

Create a frida hook named ``hook_flutter_disable_ssl.js`` with the following content. 
If needed, **replace the search pattern** and **disable adding** ``0x01`` **on ARMv8**.

.. code:: javascript

  function hook_ssl_verify_result(address)
  {
    Interceptor.attach(address, {
      onEnter: function(args) {
        console.log("Disabling SSL validation")
      },
      onLeave: function(retval)
      {
        console.log("Retval: " + retval)
        retval.replace(0x1);
  
      }
    });
  }
  function disablePinning()
  {
  var m = Process.findModuleByName("libflutter.so"); 
  var pattern = "2d e9 f0 4f a3 b0 81 46 50 20 10 70" // MyBMW 1.5.1 to 1.7.0 (all regions)
  

  var res = Memory.scan(m.base, m.size, pattern, {
    onMatch: function(address, size){
        console.log('[+] ssl_verify_result found at: ' + address.toString());
  
        // Add 0x01 because it's a THUMB function 
        // Otherwise, we would get 'Error: unable to intercept function at 0x9906f8ac; please file a bug'
        // REQUIRED ON ARMv7 ONLY!!
        hook_ssl_verify_result(address.add(0x01));
        
      }, 
    onError: function(reason){
        console.log('[!] There was an error scanning memory');
      },
      onComplete: function()
      {
        console.log("All done")
      }
    });
  }
  setTimeout(disablePinning, 1000)

Connect to your phone via ADB with root permissions.

.. code:: bash

  adb root && adb remount

Update & start frida server on the phone with ``frida-android-helper``.

.. code :: bash

  fah server update && fah server start

Start the MyBMW app from your computer via ``frida`` (adjust app identifier if needed).

.. code:: bash

  frida -Uf de.bmw.connected.mobile20.row -l .\hook_flutter_disable_ssl.js --no-pause

Now you should be able to capture all traffic between your phone and the MyBMW API.

Using the information in bimmer_connected
-----------------------------------------

If you learn anything by capturing the traffic, please create `Issues/Feature Requests <https://github.com/bimmerconnected/bimmer_connected/issues/new/choose>`_
or `Pull Requests <https://github.com/bimmerconnected/bimmer_connected/pulls>`_ to our repository. Information that should be included contains:

* The URL of the endpoint
* HTTP headers of your request (**DO NOT** include **Cookie** or **Authentication** headers)
* The request payload (if available)
* The request response (if available)

If the data contains personal information, please do not delete it but replace it with random data.

.. warning::
  Double check if all information is **sanitized** and no personal information or authentication data is included.
