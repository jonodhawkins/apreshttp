ApRES HTTP API Routes
=====================================

All routes are postfixed to `http://[radar IP/hostname]/api/`

System Routes
~~~~~~~~~~~~~
Related to system-level configuration and management
 
`api/system/reset`
-------------------------------------------------------------------------------
Resets the ApRES radar, which may be used to attempt to
resolve RAM issues or an unresponsive radar motherboard
remotely.

-------------------------------------------------------------------------------

**Method:** POST

**Response Code:** 202 Accepted.  No reset can be guaranteed

**Response:** [application/json] reset time and message

.. code-block:: json

    {
        "message" : str,  
        "time" :    datetime str in YYYY-MM-DD HH:mm:ss
    }


`api/system/housekeeping/status`
-------------------------------------------------------------------------------
Gets the system status of the ApRES radar.  Includes 
real-time clock, GPS and battery information.

-------------------------------------------------------------------------------

**Method:** GET

**Response Code:** 200 OK

**Response:** [application/json] system status object

.. code-block:: json

    {
        "batteryVoltage"    : float,
        "timeVAB"           : datetime str in YYYY-MM-DD HH:mm:ss,
        "timeGPS"           : datetime str in YYYY-MM-DD HH:mm:ss,     
        "latitude"          : float latitude in decimal format,
        "longitude"         : float longitude in decimal format
    }

If the GPS is unavailable, ``timeGPS`` will be set to
and empty string, while latitude and longitude will be
set to zero. 

`api/system/housekeeping/config`
----------------------------
Used to get the current system `config.ini` configuration
file, or update it to a new version.

**Note:** Updated configuration files will not take effect
unless the radar is restarted.

-------------------------------------------------------------------------------

**Method:** GET

**Response Code:**

* 200 OK (config.ini exists)
* 404 Not Found if config.ini does not exist.
* 500 Internal Server Error if not filesystem is found on
  the ApRES

**Response:** [text/plain] HTTP file transfer of config.ini

-------------------------------------------------------------------------------

**Method:** POST

**Response Code:**

* 201 Created (file uploaded and renamed)
* 400 Bad Request (no file uploaded)

**Response:** [text/plain] HTTP file transfer of the updated config.ini

Radar Routes
~~~~~~~~~~~~
Related to radar-level configuration and performing bursts

`api/radar/config`
-------------------------------------------------------------------------------
Returns the current radar burst configuration, in terms of the
number of attenuator settings to use, averaging, number of 
sub bursts, RF attenuator and AF gain settings, transmit and
receive antenna selection and user-data.

-------------------------------------------------------------------------------

**Method:** GET

**Response Code:**

* 200 OK

**Response:** [application/json] config object

.. code-block:: json

    {
        "rfAttn"        : list of floats, RF attenuator settings,
        "afGain"        : list of ints, AF gain settings,
        "nSubBursts"    : int, number of chirps per 'burst' and attn. setting,
        "nAttenuators"  : int, number of attenuator settings [1 to 4],
        "nAverages"     : int, number of chirps to stack in trial burst mode,
        "txAntenna"     : list of ints, MIMO transmit antenna selection,
        "rxAntenna"     : list of ints, MIMO receive antenna selection,
        "userData"      : str, user-defined string appended to burst file headers 
    }

If the ``debug=1`` HTTP parameter is passed to the HTTP request
an additional property of the JSON object will be assigned

.. code-block:: json

    # with api/radar/config?debug=1
    {
        ...
            other config properties
        ...,
        "state" : int, debug radar state
    }

-------------------------------------------------------------------------------

**Method:** POST

**Response Code:**

* 200 OK (if burst configruation is updated successfully)
* 400 Bad Request (if HTTP parameters are malformed)

**Parameters:**

* *nAttenuators* [int, in range 1 to 4]
* *nSubBursts* [int, greater than 1]
* *nAverages* 

**Response:** [application/json] config object as for GET request

If the request is malformed (i.e. 400 Bad Request) then an error message
is returned.  See [LINK] for more information.


`api/radar/trial-burst`
-------------------------------------------------------------------------------
Performs a trial burst with the radar.  If `nAverages` in the radar 
configuration is set to greater than 1, then `nAverages` chirps are performed
and their results are averaged.  Results from the trial bursts can be 
retrieved from the radar using the ``api/radar/results`` route.

------------------------------------------------------------------------------

**Method:** POST

**Response Code:**

* 303 See other (if the trial burst is started, with redirect to results URL)
* 403 Forbidden (The radar is already performing a burst so cannot continue)

`api/radar/burst`
-------------------------------------------------------------------------------
Performs a full burst with the radar, with the data saved to the optional
filename provided.

-------------------------------------------------------------------------------

**Method:** POST

**Parameters:**

* *filename* [str, filename to save data to]
* *userData* [str, 32 char user data for file]

**Response Code:**

* 303 See Other (Redirect to the results URL if the burst has started)
* 403 Forbidden (The radar is already performing a burst so cannot continue)
* 403 Forbidden (The filename provided already exists)
  
------------------------------------------------------------------------------

**Method:** POST

**Response Code:**

* 303 See other (if the trial burst is started, with redirect to results URL)
* 403 Forbidden (The radar is already performing a burst so cannot continue)



`api/radar/results`
------------------------------------------------------------------------------
If available, retrieves results from the radar from a trial burst or returns
the filename of the data file with the latest burst.

------------------------------------------------------------------------------

**Method:** GET

**Response Code:**

* 200 OK

**Response:** [application/json]

If the radar is idle, computing histograms or has an unknown state 

.. code-block:: json

    {
        "status"    : str "idle" | "histograms" | "unknown" 
    }

If the radar is chirping, from either a trial burst or full burst

.. code-block:: json

    {
        # present for all burst types
        "status"        : str "chirping",
        "type"          : str "trial" | "burst" depending on burst type
        # only present for full burst indicating sub burst count
        "chirpNumber"   : int
    }

If the radar has finished a trial or full burst

.. code-block:: json

    {
        # present for all results 
        "status"        : "finished", 
        "type"          : "trial" | "burst",
        "nAttenuators"  : int, number of attenuator settings,
        "rfAttn"        : list (nAttenuators length) of list of floats,
        "afGain"        : list (nAttenuators length) of list of ints,
        "startFrequency": int, chirp start frequency in Hz
        "stopFrequency" : int, chirp stop frequency in Hz
        "period"        : int, chirp period in seconds
        # present for full burst results only
        "nSubBursts"    : int, number of sub bursts per attenuator setting,
        "filename"      : str, file path to location of dataset
        # present for trial burst results only
        "histogram"     : list (nAttenuators length) of list of ints,
        "chirp"         : list (nAttenuators length) of list of ints,
        "nAverages"     : int, number of averages used    
    } 

Data Routes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Related to download and browsing of file system
 
`api/data/dir`
----------------------------
Returns a directory listing of either the root directory on the SD card or 
a specified folder.  The number of elements returned per request can be 
chosen with the `list` parameter, and the start index is given by the 
`index` parameter

-------------------------------------------------------------------------------

**Method:** GET

**Parameters:**

* *index* [int, start index to list directory entries from]
* *list* [int, number of directory entries per page]
* *path* [str, path to file object to observe]

**Response Code:**

* 200 OK
* 404 Not Found (i.e. file or directory not found)

**Response:** [application/json]

If the path points to a file object

.. code-block:: json

    {
        "index"     : int, index of file object within list of directory elements,
        "dir"       : int, 1 if the file object is a directory, 0 if a file,
        "timestamp" : str, YYYY-MM-DD HH:mm:ss timestamp last modified datatime,
        "size"      : int, size file object on SD card,
        "path"      : str, full path to file object,
        "name"      : str, name part of file path
    }

Or if the path points to a directory

.. code-block:: json

    {
        "path"      : str, path to directory, 
        "fileCount" : int, total number of file objects in directory,
        "index"     : int, start index for file objects listed in files,
        "list"      : int, number of file objects in files,
        "length"    : int, total number of file objects in directory,
        "files"     : [
            ...
            list of JSON objects representing file objects (see above)
            ... 
        ]
    }

`api/data/download`
----------------------------
Downloads a file from the file system, if the path exists

-------------------------------------------------------------------------------

**Method:** GET

**Parameters:**

* *path* [str, path to file object]

**Response Code:**

* 200 OK
* 403 Forbidden (cannot download a directory)
* 404 File not found

**Response:** [file object]