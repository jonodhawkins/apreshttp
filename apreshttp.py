# Python wrapper for HTTP API to Control the ApRES Radar
import datetime
import os
import json
import os
import re
import requests
import time
import threading

class API:
    """
    Entry-point class for Python code to access HTTP ApRES API

    The API class exposes the system, radar and data top-level elements
    of the ApRES HTTP API.  It also exposes methods for assigning the
    API key required to perform POST requests.

    POST requests are used to perform operations on the radar (such as
    bursts updating configuration, etc.) and as such require the API
    key to provided.
    """

    def __init__(self, root):
        """
        Initialise a new instance of the API specifying the root URL

        Creating a new instance of the API class requires the provision
        of a root URL.

        The default URL used by the ApRES is

            http://radar.localnet OR
            http://192.168.1.1

        The root URL is sanitised by API.assignRootURL - see this for
        further information.

        :param root: Root URL for the API to direct HTTP requests to
        :type root: str
        """

        # Set root URL
        self.assignRootURL(root)

        # Assign root objects
        self.system = System(self)
        self.radar = Radar(self)
        self.data = Data(self)

        # Assign default repeat requests/timeout
        self.timeout = 30 #: HTTP timeout in seconds
        self.wait = 1 #: wait time between consecutive HTTP requests

        # Whether to output debug commands
        self.debugEnable = False

        self.apiKey = "INVALID"

    def debug(self, *args, **kwargs):
        """
        Prints to the default system output buffer, if debug enabled

        Prints to the default system output buffer, as used by the
        system `print` function.

        :param \*args: unpack unnamed arguments into print
        :param \*\*kwargs: unpack named keywork arguments into print
        """

        if self.debugEnable:
            print(*args, **kwargs)

    def setKey(self, key):
        """
        Sets the API key to be used during POST requests

        :param key: string key to be used for API requests
        :type key: str
        :raises InvalidAPIKeyException: raised if the key parameter is not a string or is empty.
        """

        if isinstance(key, str) and len(key) > 0:
            self.apiKey = key
        else:
            raise InvalidAPIKeyException

    def assignRootURL(self, root):
        """Sanitises and assigns the value in root as the root API URL

        Checks whether the value in root is formatted correctly as the
        root URL for the API.

        Values for root can be preceeded with 'http://' or omit the
        'http://' protocol.  Trailing forward slashes will be trimmed
        from the root URL if present.

        Empty text at the start of the root URL is stripped, however no
        guarantee is given that the URL will connect when API functions
        are called.

        :param root: root URL for the api (i.e. http://radar.localnet)
        :type root: str
        :raises TypeError: raised if the root parameter is not a str
        """

        # Check whether the root is a string
        if not isinstance(root, str):
            raise TypeError("Root directory should be in string format, i.e. http://radar.localnet")

        # Check whether there is a leading "http://" or not
        http_idx = root.find("http://")
        if http_idx > 0:
            # There is some preceeding text to the "http://" - strip it
            root = root[http_idx:]
        elif http_idx == -1:
            # No "http://" provided - add it
            root = "http://" + root

        # Check for trailing slash
        if root[-1] == "/":
            # Remove trailing character
            root = root[0:-1]

        self.root = root

class APIChild:
    """
    APIChild objects provide wrappers for POST and GET requests

    APIChild objects wrap the :py:func:`requests.get` and
    :py:func:`requests.post` methods to build classes to support the
    implementation of calls of GET and POST API methods.
    """

    def __init__(self, api_obj):
        """
        Assign instance of the :py:class:`API` class

        APIChild should inherently be a child of an :py:class:`API` object
        hence the constructor requires an instance of :py:class:`API` to
        meet this conditions.

        :param api_obj: instance of :py:class:`API`
        :type api_obj: apreshttp.API
        """

        self.api = api_obj

    def postRequest(self, url, data_obj = None, files_obj = None):
        """
        Perform a POST request to the URL, passing an API key and data

        The URL should be a valid ApRES HTTP API URL as described in
        :any:`api_routes`, without the `api/` or root prefix.  If the
        URL is not valid then a NotFoundException is raised.

        HTTP arguments can be passed using the `data_obj` parameter as
        a dictionary, containing named arguments (["name"]=value).
        Acceptable value types are `str`, `float`, `int`.

        If files are to be uploaded, then they should be provided to
        the `files_obj` parameter.  The HTTP variable name is the
        dictionary key and the value is two-element tuple describing
        the filename and its content
        (i.e. ["name"] = (filename, file_content)).

        :param url: URL to be requested from the API.  Should not include the API root (i.e. http://radar.localnet/api/)
        :param data_obj: Name-value pairs to be passed as HTTP args
        :param files_obj: Dictionary of name-value pairs, where the name represents the HTTP variable name and the value is a two-element tuple of (filename, file_content)

        :type data_obj: dict
        :type url: str
        :type files_obj: dict

        """

        # Form complete URL
        completeUrl = self.formCompleteURL(url);

        # If the data object was empty, then create one and assign the local
        # API key for use in the post request
        if data_obj == None:
            data_obj = dict()
            data_obj['apikey'] = self.api.apiKey
        # Otherwise, check whether an API key was provided and if not add one
        # using the local API key value
        elif "apikey" not in data_obj.keys():
            data_obj["apikey"] = self.api.apiKey

        self.api.debug("POST request to [{url:s}] with data:".format(url=completeUrl))
        self.api.debug(data_obj)

        # Create request object
        if files_obj == None:
            response = requests.post(
                completeUrl,
                data = data_obj,
                timeout = self.api.timeout
            )
        else:
        # If files is set then add that
            response = requests.post(
                completeUrl,
                data = data_obj,
                files = files_obj,
                timeout = self.api.timeout
            )

        self.api.debug("Validating...")
        # Check for errorCode and errorMessage keys
        self.validateResponse(response)

        self.api.debug("Passed.")

        # Return the response for the function to do something with
        return response

    def getRequest(self, url, data_obj = None):
        """
        Perform a GET request to the URL, passing an API key and data

        The URL should be a valid ApRES HTTP API URL as described in
        :any:`api_routes`, without the `api/` or root prefix.  If the
        URL is not valid then a NotFoundException is raised.

        HTTP arguments can be passed using the `data_obj` parameter as
        a dictionary, containing named arguments (["name"]=value).
        Acceptable value types are `str`, `float`, `int`.  This is the
        same as requesting a URL with a query string appended with

            ?name1=value1&name2=value2

        :param url: URL to be requested from the API which is append to the root in the form {root}/api/{url}
        :param data_obj: Name-value pairs to be passed as HTTP args

        :type data_obj: dict
        :type url: str

        """

        # Form complete URL
        completeUrl = self.formCompleteURL(url);

        # If data object is empty, convert into an empty dict
        if data_obj == None:
            data_obj = dict()

        self.api.debug("GET request to [{url:s}] with data:".format(url=completeUrl))
        self.api.debug(data_obj)

        # Create request object
        response = requests.get(
            completeUrl,
            data = data_obj,
            timeout = self.api.timeout
        )

        self.api.debug("Validating...")
        self.validateResponse(response)
        self.api.debug("Passed.")

        return response

    def validateResponse(self, response):
        """
        Takes a `requests.response` object and handles common errors

        If the response is JSON and contains the errorCode and
        errorMessage keys, then parse these and raise the appropriate
        exceptions.

        :param response: `response` object returned from :py:meth:`getRequest` or :py:meth:`postRequest`
        :type response: request.response object

        :raises InvalidAPIKeyException: API key is invalid
        :raises NotFoundException: Requested URL was not found/invalid
        :raises InternalRadarErrorException: Problem with the radar described in the error text.
        :raises RadarBusyException: Radar could not perform requested task because it is busy.
        """

        # Check  we have a JSON object
        if "Content-Type" in response.headers.keys() and response.headers["Content-Type"] == "application/json":
            # Default checking GET and POST requests
            response_json = response.json()
            if "errorCode" in response_json or "errorMessage" in response_json:
                if response_json['errorCode'] == 401:
                    raise InvalidAPIKeyException(response_json['errorMessage'])
                elif response_json['errorCode'] == 404:
                    raise NotFoundException(response_json['errorMessage'])
                elif response_json['errorCode'] == 500:
                    raise InternalRadarErrorException(response_json['errorMessage'])
                elif response_json['errorCode'] == 503:
                    raise RadarBusyException(response_json['errorMessage'])


    def formCompleteURL(self, url_part):
        """
        Returns the full URL for the HTTP request

        Combines the API root, /api/ component and final API route into
        a complete URL, i.e.

            system/reset => http://radar.localnet/api/system/reset

        :param url_part: API route, i.e. system/reset
        :type url_part: str
        :return: str
        """
        return self.api.root + "/api/" + url_part

################################################################################
# SYSTEM
################################################################################

class System(APIChild):
    """
    System wraps system-related API methods

    System provides a wrapper for the system-related functions exposed
    by the ApRES HTTP API.  This includes

    * system/reset
    * system/housekeeping/config
    * system/housekeeping/status
    """

    def __init__(self, api_obj):
        # Call super constructor
        super().__init__(api_obj)

        # Create housekeeping sub object
        self.housekeeping = self.Housekeeping(api_obj)

    # System reset
    def reset(self):
        """
        Reset the ApRES

        Requires a valid API key to be assigned to the API object to
        perform the reset operation.

        No guarantee of a reset can be made, but upon successful
        reception of the request a
        :py:class:`apreshttp.System.ResetMessage` object is returned.

        :raises BadResponseException: If the response is malformed or unexpected.
        """

        # Get response
        response = self.postRequest("system/reset")
        # Check the status code is 202 (i.e. don't wait...)
        if response.status_code != 202:
            raise SystemResetException
        else:
            # Strip message and time from response
            response_json = response.json()

            if not "message" in response_json:
                raise BadResponseException("No message key in response.")
            msg = response_json["message"]

            if not "time" in response_json:
                raise BadResponseException("No time key in response.")
            time = datetime.datetime.strptime(
                response_json["time"],
                "%Y-%m-%d %H:%M:%S"
            )

        return self.ResetMessage(msg, time)

    class ResetMessage:
        """
        Utility class to contain message and time from reset action
        """
        def __init__(self, msg, time):
            #: Reset message, including timestamp.
            self.message = (msg)
            #: Datetime object representing time of reset
            self.time = (time)

    class Housekeeping(APIChild):
        """
        Housekeeping encapsulates system config and status methods

        The Housekeeping object should be a child of the System object
        and exposes methods to download the configuration file, upload
        and new configuration file or retrieve the radar system status,
        packaged in a :py:class:apreshttp.System.Housekeeping` object.

        """

        def __init__(self, api_obj):
            self.api = api_obj
            self.config = self.Config(api_obj)

        def status(self):
            """
            Request an update on the ApRES battery, tiem, GPS, etc.

            Perform a GET request to system/housekeeping/status and
            wrap the response as a
            :py:class:`apreshttp.System.Housekeeping.Status` object.

            :raises BadResponseException: if the response is malformed or missing information.
            :return: If valid a :py:class:`apreshttp.System.Housekeeping.Status` object is returned

            """
            # Get response
            response = self.getRequest("system/housekeeping/status")
            # Check that the status code is 200
            if response.status_code != 200:
                raise SystemHousekeepingException(
                "Unexpected status code: {stat:d}".format(stat=response.status_code))
            else:
                # Convert response body to JSON
                response_json = response.json()

                self.api.debug(response.text)

                # Check response has valid components
                if not "batteryVoltage" in response_json:
                    raise BadResponseException("No batteryVoltage key in response.")
                if not "timeGPS" in response_json:
                    raise BadResponseException("No timeGPS key in response.")
                if not "timeVAB" in response_json:
                    raise BadResponseException("No timeVAB key in response.")
                if not "latitude" in response_json:
                    raise BadResponseException("No latitude key in response.")
                if not "longitude" in response_json:
                    raise BadResponseException("No longitude key in response.")

                return self.Status(
                    response_json["batteryVoltage"],
                    response_json["timeGPS"],
                    response_json["timeVAB"],
                    response_json["latitude"],
                    response_json["longitude"],
                )

        class Status:
            """
            Utility class for representing the ApRES system status.
            """
            def __init__(self, batVoltage, timeGPS, timeVAB, lat, long):

                # Assign batteryVoltage
                if isinstance(batVoltage, float) or isinstance(batVoltage, int):
                    #: Reported ApRES battery voltage (may be 0 if not enabled or connected)
                    self.batteryVoltage = batVoltage
                else:
                    raise BadResponseException("batteryVoltage should be a numeric type.")

                # Assign latitude
                if isinstance(lat, float) or isinstance(lat, int):
                    #: Reported latitude from GPS
                    self.latitude = lat
                else:
                    raise BadResponseException("latitude should be a numeric type.")

                # Assign longitude
                if isinstance(long, float) or isinstance(long, int):
                    #: Reported longitude from GPS
                    self.longitude = long
                else:
                    raise BadResponseException("longitude should be a numeric type.")

                #: GPS timestamp as a :py:class:`datetime.datetime` object, if available.
                self.timeGPS = None
                # Assign GPS time
                if isinstance(timeGPS, str):
                    if len(timeGPS) > 0:
                        self.timeGPS = datetime.datetime.strptime(timeGPS, "%Y-%m-%d %H:%M:%S")
                else:
                    raise BadResponseException("timeGPS should be a string containing YYYY-mm-DD HH-MM-SS timestamp.")


                #: VAB timestamp as a :py:class:`datetime.datetime` object
                self.timeVAB = None
                # Assign VAB time
                if isinstance(timeVAB, str):
                    if len(timeVAB) > 0:
                        self.timeVAB = datetime.datetime.strptime(timeVAB, "%Y-%m-%d %H:%M:%S")
                else:
                    raise BadResponseException("timeVAB should be a string containing YYYY-mm-DD HH-MM-SS timestamp.")

        class Config(APIChild):
            """
            Config class facilitates up/download of the system config

            The Config class allows for the remote config.ini file to
            be downloaded onto the local filesystem, or a replacement
            config file to be uploaded.

            NOTE: The ApRES must be restarted before a newly uploaded
            config.ini file will take effect.

            """

            def download(self, fileLocation = None, overwrite = False):
                """
                Download ApRES config.ini to the local filesystem

                If a directory is specified for the file location then
                the function will look for an existing `config.ini`
                file.  If an existing `config.ini` file exists in that
                directory then it will be overwritten if the overwrite
                option is enabled.

                If a file is specified for the file location then if it
                does not exist, it will be created.  If it does exist
                and overwrite is enabled it will be overwritten,
                otherwise a FilExistsError is raised.

                :param fileLocation: file system path to where the config.ini file should be downloaded
                :param overwrite: if the file exists, then overwrite

                :type fileLocation: str
                :type overwrite: boolean

                :raises FileExistsError: Raised if the file exists and overwrite is not enabled.

                """
                # If fileLocation is None then default to "config.ini"
                if fileLocation == None:
                    fileLocation = "config.ini"

                # Get response
                response = self.getRequest("system/housekeeping/config")
                # Check whether the file location is valid and exists
                if os.path.isdir(fileLocation):
                    fileLocation = os.path.join(fileLocation, "config.ini")

                if os.path.isfile(fileLocation):
                    if not overwrite:
                        raise FileExistsError

                with open(fileLocation, 'w') as fh:
                    print(response.text, file=fh)

                return True

            def upload(self, fileLocation = None):
                """
                Upload new ApRES config.ini file from the filesystem

                If a directory is specified for the file location then
                the function will look for a config.ini file within
                that directory.  Otherwise, if a file is specified
                then that is uploaded.

                If the file does not exist (or a file named config.ini
                within the directory) then a FileNotFoundError is
                raised.

                The files are renamed to config.ini by the ApRES radar
                when they are uploaded.

                :param fileLocation: file system path to where the config.ini file should be uploaded from.

                :type fileLocation: str

                :raises FileNotFoundError: Raised if the file at fileLocation, or a "config.ini" file within that directory, is not found.
                :raises NoFileUploadedError: Raised if the request was malformed and no file was uploaded.
                :raises BadResponseException: The response was malformed or the response was not a HTTP 201 status code.

                """

                if os.path.isdir(fileLocation):
                    fileLocation = os.path.join(fileLocation, "config.ini")

                if not os.path.isfile(fileLocation):
                    raise FileNotFoundError

                # Get response
                with open(fileLocation) as fh:
                    content = fh.read()
                    fileDict = dict()
                    fileDict["file"] = ("config.ini", content)
                    response = self.postRequest(
                        "system/housekeeping/config",
                        data_obj = None,
                        files_obj = fileDict
                    )

                    if response.status_code == 400:
                        raise NoFileUploadedError
                    elif response.status_code != 201:
                        raise BadResponseException

################################################################################
# RADAR
################################################################################

class Radar(APIChild):
    """
    Wrapper class for radar operation and configuration

    The Radar class exposes methods in the API to update the chirp
    settings, perform trial bursts and collect results, and perform
    a radar measurement (burst).
    """

    def __init__(self, api_obj):
        super().__init__(api_obj);
        # Create child of type Config
        #: Instance of a Radar.Config object which gets and sets the radar chirp config.
        self.config = self.Config(api_obj)

    def trialBurst(self, callback = None, wait = True):
        """
        Perform a trial burst using the current configuration

        Attempts to start an asynchronous trial radar burst, using the
        current configuration. Also retrieves configuration from the
        API.

        If the burst starts successfully then the response status code
        should be 303 and redirect to the "results" API route.

        If the status code is 403 then something is preventing the
        radar from starting the burst.

        To parse the results from the trial burst, the below gives some
        example code:

        .. code-block:: python

            # Create API instance
            api = apreshttp.API("http://radar.localnet")
            api.API_KEY = [...]

            # Define callback function
            def trialResultsCallback(response):
                try:
                    response_json = response.json()
                    # DO SOMETHING WITH RESULTS
                    ...
                except:
                    print("Couldn't read results.")

            # Perform trial burst
            api.radar.trialBurst(trialResultsCallback) # will hang until results are returned.

        :param callback: If provided, callback is executed when results are available.  The callback function should take a single argument of type requests.response
        :type param: callable
        :param wait: If callback is provided, should the function halt execution or wait in a seperate thread
        :type wait: boolean
        :type :raises BurstNotStartedException: Raised if the API returns a 403 indicating the radar cannot start the burst.  Might happen if the burst is already started, for example.

        """

        if callback != None and not callable(callback):
            raise TypeError("Argument 'callback' should be callable.")

        # Update config locally
        self.config.get()

        # Make a POST request to trial burst
        response = self.postRequest("radar/trial-burst")

        # Check whether the burst started (any other status codes )
        if response.status_code != 303:

            # Get response
            response_json = response.json()
            if "errorMessage" in response_json:
                raise BurstNotStartedException(response_json["errorMessage"])
            else:
                raise BurstNotStartedException

        if callback != None:
            self.results(callback, wait)

    def results(self, callback, wait = True):
        """
        Wait for results to be returned by the radar
        """

        if not callable(callback):
            raise TypeError("Argument 'callback' should be callable.")

        # If waiting, run in the same thread
        if wait:
            self.__getResults(callback)
        # Otherwise create a new thread and start it
        else:
            resultsThread = threading.start(self.__getResults, args=(callback))
            resultsThread.start()


    def __getResults(self, callback):
        """
        Nothing to see here...
        """

        # Update config
        self.config.get()

        # Define initiation time
        init_time = datetime.datetime.now()

        # Calculate timeout (allow 2 seconds for each chirp)
        timeoutSeconds = self.config.nSubBursts * \
                         self.config.nAttenuators * 2 + self.api.timeout

        self.api.debug("Getting results [Timeout = {timeout:f]".format(
            timeout=timeoutSeconds
        ))

        timeout = datetime.timedelta(seconds = timeoutSeconds)

        # Loop until we timeout
        while (datetime.datetime.now() - init_time < timeout):

            # Make GET request to results
            response = self.getRequest("radar/results")
            response_json = response.json()

            # Check if a chirp was requested
            if response_json["status"] == "sleeping":
                # No chirp was started so break
                raise NoChirpStartedException

            elif response_json["status"] == "chirping":
                pass

            elif response_json["status"] == "finished":
                callback(self.Results(response))

        raise ResultsTimeoutException

    def burst(self):
        """
        Perform a measurement radar burst using the current config

        Attempts to start an asynchronous radar burst, using the
        current configuration.  Also retrieves configuration from the
        API.

        If the burst starts successfully then the response status code
        should be 303 and redirect to the "results" API route.

        If the status code is 403 then something is preventing the
        radar from starting the burst.

        :raises BurstNotStartedException: Raised if the API returns a 403 indicating the radar cannot start the burst.  Might happen if the burst is already started, for example.
        """

        # Update config locally
        self.config.get()

        # Make a POST request to trial burst
        response = self.postRequest("radar/burst")

        # Check whether the burst started (any other status codes )
        if response.status_code != 303:

            # Get response
            response_json = response.json()
            if "errorMessage" in response_json:
                raise BurstNotStartedException(response_json["errorMessage"])
            else:
                raise BurstNotStartedException

    class Results:
        """
        Container class for trial-burst results
        """
        def __init__(self, response):

            response_json = response.json()

            if not "nAttenuators" in response_json:
                raise BadResponseException("No key 'nAttenuators' found in results.")

            if not "nAverages" in response_json:
                raise BadResponseException("No key 'nAverages' found in results.")

            self.nAttenuators = int(response_json["nAttenuators"])
            self.nAverages = int(response_json["nAverage"])

            # Create empty list for results
            self.range = []


            # Iterate over number of attenuators
            for attnIdx in range(self.nAttenuators):
                # TODO: Add code to parse results
                pass



    class Config(APIChild):
        """
        Retrieve and modify radar burst configuration

        The Radar.Config class can be updated from the API using the :py:meth:`get` method.

        If it is desired to change values, such as individual
        attenuator settings or the number of sub-bursts, then the
        :py:meth:`set` method should be used.

        NOTE: when instance attributes, such as :py:attr:`nAttenuators`
        are accessed, these are not automatically updated from the API
        and default to their last values, hence care should be taken
        to call :py:meth:`get` when it is desired to have the most
        recent configuration values.

        By default, instance variables are initialised to `None` until
        a :py:meth:`get` request is made.
        """

        def __init__(self):
            #: Number of attenuator settings (int)
            self.nAttenuators = None
            #: Number of sub-bursts per burst (int)
            self.nSubBursts = None
            #: Number of averages for a trial burst (int)
            self.nAverages = None
            #: RF attenuator settings (list of float)
            self.afGain = []
            #: AF gain settings (list of float)
            self.rfGain = []

        def get(self):
            """
            Retrieve the latest radar burst configuration

            :return: Returns `self`

            :raises BadResponseException: Raised in the event of an unexpected error code or missing JSON keys.
            """

            # Get response
            response = self.getRequest("radar/config")
            #
            if response.status_code != 200:
                raise BadResponseException(
                "Unexpected status code: {stat:d}".format(stat=response.status_code))
            else:
                readResponse(response)

        def readResponse(self, response):
            """
            Read values from a response to radar/config into Config object

            :raises BadResponseException: Raised if there are missing fields from the radar configuration JSON response.
            """
            # Convert response body to JSON
            response_json = response.json()

            self.api.debug(response.text)

            # Check response has valid components
            if not "nSubBursts" in response_json:
                raise BadResponseException("No nSubBursts key in response.")
            if not "nAttenuators" in response_json:
                raise BadResponseException("No nAttenuators key in response.")
            if not "nAverages" in response_json:
                raise BadResponseException("No nAverages key in response.")

            self.nAttenuators = response_json["nAttenuators"]
            self.nSubBursts = response_json["nSubBursts"]
            self.nAverages = response_json["nAverages"]
            # Create empty AF gain and RF attenuation arrays

            self.rfAttn = []
            self.afGain = []
            for i in range(self.nAttenuators):
                keyVal = "rfAttn" + str(i+1)
                if not keyVal in response_json:
                    raise BadResponseException("Expected " + keyVal +
                    " but not found in response.")
                self.rfAttn.append(response_json[keyVal])

                keyVal = "afGain" + str(i+1)
                if not keyVal in response_json:
                    raise BadResponseException("Expected " + keyVal +
                    " but not found in response.")
                self.afGain.append(response_json[keyVal])

            # Sanity check we have the correct number of attenuators
            if len(self.rfAttn) == self.nAttenuators \
            and len(self.afGain) == self.nAttenuators:
                return self
            else:
                raise BadResponseException("Number of attenuator settings did not match nAttenuators in response.")

        def set(
            self, nAtts=None, nBursts=None, rfAttnSet=None, afGainSet=None,
            txAnt=None, rxAnt=None
        ):
            """
            Updates the radar burst configuration with the given parameters

            :param nAtts: Set the number of attenuator settings to be used (1-4)
            :type nAtts: int or `None`
            :param nBursts: Set the number of chirps to be averaged for a trial burst, or repeated for a full burst.
            :type nBursts: int or `None`
            :param rfAttnSet: Set the values of the ApRES RF attenuator.  If using a dictionary, keys should be "rfAttn1", "rfAttn2", etc. and may be excluded if no update is desired.
            :type rfAttnSet: int, list, dict or `None`
            :param afGainSet: Set the values of the ApRES AF gain.  If using a dictionary, keys should be "afGain1", "afGain2", etc. and may be exlcuded if no update is desired.
            :type afGainSet: int, list, dict or `None`
            :param txAnt: If using a MIMO board, set the active transmit antennas

            :type txAnt: int or list

            **NOTE**: Calling :py:meth:`set` will incur a call to
            :py:meth:`get` to retrieve the latest configuration.

            To update the number of attenuators

            .. code-block:: python

                Config.set(nAtts = 3)

            To update the number of sub-bursts

            .. code-block:: python

                Config.set(nBursts = 10)

            To update RF attenuator or AF gain values (i.e. replace
            rfAttnSet with afGainSett)

            .. code-block:: python

                # Update rfAttn1 to 16.5 dB
                Config.set(rfAttnSet = 16.5)
                # Update rfAttn1, rfAttn2 and rfAttn4 using list
                Config.set(rfAttnSet = [0, 10, None, 23.5])
                # Update using rfAttn2 and rfAttn3 using dict
                rfSettings = {"rfAttn2" : 12.5, "rfAttn3" : 6.0}
                Config.set(rfAttnSet = rfSettings)

            **WARNING**: If nAttenuators has been set in the same or a
            previous call to :py:meth:`set` and an RF attenuator or AF
            gain value with an index greater than nAtts has been set,
            then an error is thrown, i.e.

            .. code-block:: python

                # Set nAtts to 2, but try setting rfAttn3
                Config.set(nAtts = 2, rfAttnSet = [0, 10, 20])
                # Exception occurs!
                ...
                Config.set(afGainSet = [-14, -14, -14])
                # Exception occurs (trying to change nAtts to 3)

            Similarly, trying to assign a single attenuator value when
            nAttenuators is greater than 1 will cause an error

            .. code-block:: python

                # Set nAtts to 2
                Config.set(nAtts = 2)
                # Try to assign a single attenuator value
                Config.set(afGainSet = -4)
                # Exception occurs

            If using a MIMO board, providing txAnt or rxAnt with an eight
            element tuple allows the user to choose which antennas are
            enabled, i.e.

            .. code-block:: python

                # Use the 1st, 4th and 8th antennas to transmit
                Config.set(txAnt = (1,0,0,1,0,0,0,1))
                # Use the 2nd and 7th antennas to receive
                Config.set(rxAnt = (0,1,0,0,0,0,1,0))

            """

            # Update parameters
            self.get()

            # Create an empty dictionary to hold data for post request
            data_obj = dict()

            if nAtts != None:
                # Check whether nAtts is a number
                if isinstance(nAtts, int) or isinstance(nAtts, float):
                    data_obj["nAttenuators"] = nAtts
                else:
                    raise ValueError("nAtts should be numeric")

            if nBursts != None:
                # Check whether nBursts is a number
                if isinstance(nBursts, int) or isinstance(nBursts, float):
                    data_obj["nSubBursts"] = nBursts
                else:
                    raise ValueError("nBursts should be numeric")

            valid_rf = None
            if rfAttnSet != None:
                valid_rf = parseRFAttnAFGain("rfAttn", rfAttnSet, nAtts)
                if len(valid_rf) > 0:
                    # Merge valid with data_obj
                    data_obj = {**data_obj, **valid_rf}

            valid_af = None
            if afGainSet != None:
                valid_af = parseRFAttnAFGain("afGain", afGainSet, nAtts)
                if len(valid_af) > 0:
                    # Merge valid with data_obj
                    data_obj = {**data_obj, **valid_af}

            # Now deal with the request
            response = self.postRequest("radar/config", data_obj)

            # Need to check status codes in response
            if response.status_code == 400:
                response_json = response.json()
                raise BadResponseException(response_json['errorMessage'])

            elif response.status_code == 200:
                # Update object from response
                readResponse(response)
                # Check whether new values match updated values
                if nAtts != None and nAtts != self.nAttenuators:
                    raise DidNotUpdateException("nAttenuators did not update.")

                if nBursts != None and nBursts != self.nSubBursts:
                    raise DidNotUpdateException("nSubBursts did not update.")

                if valid_rf != None:
                    # Iterate over valid_rf
                    for key, value in valid_rf.items():
                        # Take last character as index
                        idx = int(key[-1]) - 1
                        # Check values match
                        self.api.debug("RF Assigned: {srv:d} vs. Retrieved: {mem:}".format(srv = value, mem = self.rfAttn[idx]))
                        if value != self.rfAttn[idx]:
                            raise DidNotUpdateException(key + " did not update.")

                if valid_af != None:
                    # Iterate over valid_af
                    for key, value in valid_af.items():
                        idx = int(key[-1]) - 1
                        # Check values match
                        self.api.debug("AF Assigned: {srv:d} vs. Retrieved: {mem:}".format(srv = value, mem = self.afGain[idx]))
                        if value != self.afGain[idx]:
                            raise DidNotUpdateException(key + " did not update.")

                # Return config object
                return self

        def parseRFAttnAFGain(self, type, arg, nAtts):
            """
            Validate RF attenuation and AF gain parameters to :py:meth:`get`

            :raises ValueError: Raised if nAtts is greater than 1 and a single AF or RF value is provided.
            :raises KeyError: Raised if the key in `arg` does not match rfAttn[1-4] or afGain[1-4]
            """

            # Check type is valid
            if not (type == "rfAttn" or type == "afGain"):
                raise Exception ("Invalid type, should be 'rfAttn' or " + "'afGain' case sensitive.")

            resp = dict()

            if isinstance(arg, int) or isinstance(arg, float):
                # Value is singular - current nAtts should be 1 and
                # updating value empty, or updating value should be 1
                if (nAtts != None and nAtts == 1) or \
                   (nAtts == None and self.nAtts == 1):
                   # Assign value to rfAttn1 or afGain1
                   resp[type + "1"] = arg
                else:
                    raise ValueError("nAtts or current nAttenuators > 1, cannot add a sigular " + type + " parameter")

            elif isinstance(arg, list):
                # If the argument is a list, it should have the same
                # number of elements as nAtts or nAttenuators
                if ((nAtts != None and len(arg) == nAtts) or (nAtts == None and len(arg) == self.nAtts)):
                   # len(arg) must be valid, therefore iterate
                   for i in range(len(arg)):
                       # Check that the value is numeric
                       if isinstance(arg[i], int) or isinstance(arg[i], float):
                           resp[type + str(i + 1)] = arg[i]
                           # otherwise ignore it and don't add that value
                           # i.e. we can have [0, None, 10] and only assign
                           #  rfAttn1 and rfAttn3 leaving rfAttn2 as is
                else:
                   raise ValueError("If " + type + "Set is a list, it should have the same number of elements as the number of attenuators")

            elif isinstance(arg, dict):
                # If the argument is a dictionary, then iterate over
                # the keys and check they are valid
                #
                # First of all, get the correct number of attenuators
                # and store in nAtts
                if nAtts == None:
                    nAtts = self.nAtts

                # Create regexp for key validation
                # (this only works if nAtts <= 9, currently 4)
                regexp = type + "([1-" + str(nAtts) + "])"

                for key, val in args.items():
                    # Find type in the key at index 0
                    match = re.search(regexp, key)
                     # check that it occurs at the start
                    if match != None and match.span()[0] == 0:
                        resp[key] = val
                    else:
                        raise KeyError("Invalid key '" + key + "' in "
                            + type + " argument.")

            return resp


################################################################################
# DATA
################################################################################

class Data(APIChild):

    def __init__(self, api_obj):
        super().__init__(api_obj);

################################################################################
# Exceptions

class InvalidAPIKeyException(Exception):
    pass

class InternalRadarErrorException(Exception):
    pass

class RadarBusyExceptio(Exception):
    pass

class NotFoundException(Exception):
    pass

class SystemResetException(Exception):
    pass

class SystemHousekeepingException(Exception):
    pass

class BadResponseException(Exception):
    pass

class NoFileUploadedError(Exception):
    pass

class BurstNotStartedException(Exception):
    pass

class NoChirpStartedException(Exception):
    pass

class ResultsTimeoutException(Exception):
    pass
