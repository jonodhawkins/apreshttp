Example Code
============

Class members are designed to have names to mimimc the REST API, so download the configuration file which would be performed by a GET request to

  http://radar.localnet/api/system/housekeeping/config

we can do the following

.. code-block:: python

    # Create new API object to interact with the ApRES at "http://radar.localnet"
    api_instance = API("http://radar.localnet")

    # Download the latest config file to the current working directory
    # Note that the members system.housekeeping.config match the REST URL

    if api_instance.system.housekeeping.config.download("my_config_file.ini"):
      # File downloaded successfully
      ... do something with the config file

To check the ApRES status, using the previously created instance of the API

.. code-block:: python

  # Try to get the status
  try:
    status = api_instance.system.housekeeping.status()
  except:
    print("Something went wrong!")

  # Check that battery voltage
  if status.batteryVoltage > 5.5:
    print("Battery okay.")
