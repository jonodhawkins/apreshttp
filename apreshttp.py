# Python wrapper for HTTP API to Control the ApRES Radar
import datetime
import os
import json
import os
import re
import requests
import time

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
        self.timeout = 30 # Seconds

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

    def __init__(self, api_obj):
        super().__init__(api_obj);
        # Create child of type Config
        self.config = self.Config(api_obj)

    class Config(APIChild):

        def get(self):
            # Get response
            response = self.getRequest("radar/config")
            #
            if response.status_code != 200:
                raise SystemHousekeepingException(
                "Unexpected status code: {stat:d}".format(stat=response.status_code))
            else:
                # Convert response body to JSON
                response_json = response.json()

                self.api.debug(response.text)

                # Check response has valid components
                if not "nSubBursts" in response_json:
                    raise BadResponseException("No nSubBursts key in response.")
                if not "nAttenuators" in response_json:
                    raise BadResponseException("No nAttenuators key in response.")

                self.nAttenuators = response_json["nAttenuators"]
                self.nSubBursts = response_json["nSubBursts"]

                return self

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
