# Python wrapper for HTTP API to Control the ApRES Radar
import datetime
import os
import json
import os
import re
import requests
import time

class API:

    def __init__(self, root):

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
        if self.debugEnable:
            print(*args, **kwargs)

    def setKey(self, key):
        if isinstance(key, str) and len(key) > 0:
            self.apiKey = key
        else:
            raise InvalidAPIKeyException

    def assignRootURL(self, root):

        # Check whether the root is a string
        if not isinstance(root, str):
            raise TypeError("Root directory should be in string format, i.e. http://radar.localnet")

        # Check for trailing slash
        if root[-1] == "/":
            # Remove trailing character
            root = root[0:-1]

        self.root = root

class APIChild:

    def __init__(self, api_obj):
        self.api = api_obj

    def postRequest(self, url, data_obj = None, files_obj = None):

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
        return self.api.root + "/api/" + url_part

################################################################################
# SYSTEM
################################################################################

class System(APIChild):

    def __init__(self, api_obj):
        # Call super constructor
        super().__init__(api_obj)

        # Create housekeeping sub object
        self.housekeeping = self.Housekeeping(api_obj)

    # System reset
    def reset(self):
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
        def __init__(self, msg, time):
            self.message = (msg)
            self.time = (time)

    class Housekeeping(APIChild):

        def __init__(self, api_obj):
            self.api = api_obj
            self.config = self.Config(api_obj)

        def status(self):
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
            def __init__(self, batVoltage, timeGPS, timeVAB, lat, long):

                # Assign batteryVoltage
                if isinstance(batVoltage, float) or isinstance(batVoltage, int):
                    self.batteryVoltage = batVoltage
                else:
                    raise BadResponseException("batteryVoltage should be a numeric type.")
                # Assign latitude
                if isinstance(lat, float) or isinstance(lat, int):
                    self.latitude = lat
                else:
                    raise BadResponseException("latitude should be a numeric type.")
                # Assign longitude
                if isinstance(long, float) or isinstance(long, int):
                    self.longitude = long
                else:
                    raise BadResponseException("longitude should be a numeric type.")
                # Assign GPS time
                if isinstance(timeGPS, str):
                    if len(timeGPS) > 0:
                        self.timeGPS = datetime.datetime.strptime(timeGPS, "%Y-%m-%d %H:%M:%S")
                    else:
                        self.timeGPS = None
                else:
                    raise BadResponseException("timeGPS should be a string containing YYYY-mm-DD HH-MM-SS timestamp.")
                # Assign VAB time
                if isinstance(timeVAB, str):
                    if len(timeVAB) > 0:
                        self.timeVAB = datetime.datetime.strptime(timeVAB, "%Y-%m-%d %H:%M:%S")
                    else:
                        self.timeVAB = None
                else:
                    raise BadResponseException("timeVAB should be a string containing YYYY-mm-DD HH-MM-SS timestamp.")

        class Config(APIChild):

            def download(self, fileLocation = None, overwrite = False):

                # If fileLocation is None then default to "config.ini"
                if fileLocation == None:
                    fileLocation = "config.ini"

                # Get response
                response = self.getRequest("system/housekeeping/config")
                # Check whether the file location is valid and exists
                if os.path.isfile(fileLocation):
                    if not overwrite:
                        raise FileExistsError

                with open(fileLocation, 'w') as fh:
                    print(response.text, file=fh)

            def upload(self, fileLocation):
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
