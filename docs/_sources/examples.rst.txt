Example Code
============

Class members are designed to have names to mimimc the REST API, so download
the configuration file which would be performed by a GET request to

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

Performing a Radar Burst
------------------------
To perform a burst (or chirp) using the radar we need to set the chirp
settings and choose a filename in advance.  Then, we can perform the 
burst, wait for the results to come through and store these locally.

.. code-block:: python

    import apreshttp
    import os
    
    # Create new API object 
    api_instance = API("http://radar.localnet")

    try:
      # Update the radar chirp config
      api_instance.radar.config.set(
        nAtts = 2,              # Use two attenuator settings
        rfAttnSet = [10 20],    # Set the RF attenuations
        afGainSet = [6 6],      # Set the AF gains
        nBursts = 10            # Set the number of bursts per atten setting
      )
    
    except e:
      exit("Could not set config."))

    # Choose a filename
    filename = "my_latest_burst.dat"

    # Perform burst
    api_instance.radar.burst(filename)

    # Wait for results (blocking execution)
    try:
      api_instance.radar.results(wait = True)
    except e: 
      exit("Could not perform burst.")

    # Download the data (if the filename does not already exist locally)
    if not os.path.exists(filename):
      api_instance.data.download("Survey/" + filename)
    