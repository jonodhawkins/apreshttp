import datetime
import http.server
import http.client
import json
import os
import tempfile 
import threading
import urllib.parse
import importlib.resources

from requests.api import post

class Server(http.server.HTTPServer):
    """
    """

    def __init__(self, root='localhost', port=8000, localFolder=None):
        # Create address tuple
        super().__init__((root, port), APIRequestHandler)

        # Create dummy data dictionary
        self.testData = dict()
        
        # Create time VAB and GPS time offsets from system clock
        self.timeVABOffset = datetime.timedelta(0)
        self.timeGPSOffset = datetime.timedelta(0)

        self.gpsValid = False
        self.gpsLatitude = 0.0;
        self.gpsLongitude = 0.0

        self.batteryVoltage = 13.0
        self.latitude = 0
        self.longitude = 0

        # Radar configuration
        self.afGain = -4
        self.rfAttn = 0
        self.nAttenuators = 1
        self.nSubBursts = 1
        self.startFrequency = 2e8
        self.stopFrequency = 4e8
        self.period = 1
        self.userData = None
        self.txAntenna = (1)
        self.rxAntenna = (1)

        # Create temporary directory
        if localFolder == None:
            self.tempDir = tempfile.TemporaryDirectory()
            self.localFolder = self.tempDir.name
        else:
            self.tempDir = None
            self.localFolder = localFolder

        # Check if there is a config file in the local folder
        self.configPath = os.path.join(self.localFolder, "config.ini")
        if not os.path.exists(self.configPath):
            with open(self.configPath, 'w+') as confHandle:
                confHandle.write(importlib.resources.open_text('apreshttp.tests', 'upload_config_a.ini').read()) 

        self.serverThread = None
        self.running = False

    def start(self):
        if self.serverThread == None:
            self.running = True
            self.serverThread = threading.Thread(target=self.serve_until_stop, args=(lambda : self.running,), daemon=True).start()
        else:
            raise Exception("Server has already been started.")

    def stop(self):
        self.running = False

    def serve_until_stop(self, run):
        while run():
            self.handle_request()

    def addTestData(self, pathToData):
        pass

    def getTestData(self):
        pass

    def removeTestData(self, pathToData):
        pass 

    def getConfig(self):
        pass

    def doTrialBurst(self):
        pass

    def doBurst(self):
        pass


    def setVABTimeOffset(self, timedelta):
        if isinstance(timedelta, datetime.timedelta):
            self.timeVABOffset = timedelta
        else:
            raise Exception("VAB time offset must be specified as a datetime.timedelta object")

    def setGPSTimeOffset(self, timedelta):
        if isinstance(timedelta, datetime.timedelta):
            self.timeGPSOffset = timedelta
        else:
            raise Exception("GPS time offset must be specified as a datetime.timedelta object")

    def getVABDatetime(self):
        return datetime.datetime.now() + self.timeVABOffset

    def getGPSDatetime(self):
        return datetime.datetime.now() + self.timeGPSOffset

class APIRequestHandler(http.server.BaseHTTPRequestHandler):
    """
    """

    API_ROUTES = {
        "system" : {
            "reset" : "doSystemReset",
            "housekeeping" : {
                "status" : "doHousekeepingStatus",
                "config" : "doHousekeepingConfig"
            }
        },
        "radar" : {
            "config" : "doRadarConfig",
            "trial-burst" : "doRadarTrialBurst",
            "burst" : "doRadarBurst",
            "results" : "doRadarResults"
        },
        "api" : {
            "data" : {
                "dir" : "doDataDir",
                "download" : "doDataDownload"
            }
        }
    }

    DATETIME_FORMAT_TEXT = "%Y-%m-%d %H:%M:%S"
    DATETIME_FORMAT_FILE = "%Y-%m-%d_%h%M%S"

    API_KEY = 18052021

    def authenticatePostRequest(self):
        content_len = int(self.headers.get('content-length'))
        post_body = self.rfile.read(content_len)

        # Need to encode the response as ASCII before parsing to avoid 
        # byte data out
        parsed_data = urllib.parse.parse_qs(post_body.decode('ASCII'))

        # This could be tidied up - check that there is actually a value
        # in ['apikey'] before calling ['apikey'][0]
        return 'apikey' in parsed_data and str(parsed_data['apikey'][0]) == str(self.API_KEY)

    def responseJSON(self, code, jsonDict={}):
        self.send_response(code)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(
            json.dumps(jsonDict).encode("utf-8")
        )

    def responseError(self, errorCode=500, errorMessage="Internal server error."):
        self.responseJSON(
            code=errorCode,
            jsonDict={
                "errorCode" : errorCode,
                "errorMessage" : errorMessage
            }
        )

    def response401(self):
        self.responseError(401, "Unauthorized or API key invalid.")

    def response404(self, path=""):
        if len(path) < 1:
            path = self.path
        self.responseError(404, path)

    def response500(self):
        self.responseError(500, "Radar or VAB error")

    def response501(self):
        self.responseError(501, "Not yet implemented.")

    def response503(self):
        self.responseError(503, "VAB or Radar unavailable.")

    def doSystemReset(self):
        if self.command == "POST":
            if not self.authenticatePostRequest():
                self.response401()
            else:
                self.responseJSON(
                    code = 202,
                    jsonDict = {
                        "message" : "Resetting dummy ApRES",
                        "time" : datetime.datetime.now().strftime(self.DATETIME_FORMAT_TEXT)
                    }
                )
        else:
            self.response501()

    def doHousekeepingStatus(self):
        if self.command == "GET":

            # Create base status response
            statusDict = {
                "batteryVoltage" : self.server.batteryVoltage,
                "timeVAB" : self.server.getVABDatetime().strftime(self.DATETIME_FORMAT_TEXT),
                "timeGPS" : "",
                "latitude" : 0.0,
                "longitude" : 0.0
            } 
            # Check GPS 
            if self.server.gpsValid:
                statusDict["timeGPS"] = self.server.getGPSDatetime().strftime(self.DATETIME_FORMAT_TEXT)
                statusDict["latitude"] = self.server.latitude
                statusDict["longitude"] = self.server.longitude

            self.responseJSON(code = 200, jsonDict = statusDict)

        else:
            self.response501()

    def doHousekeepingConfig(self):
        if self.command == "GET":
            if os.path.exists(self.server.configPath):
                self.send_response(200)
                self.send_header("Content-type", "text/plain")
                self.end_headers()
                with open(self.server.configPath, 'r') as confFile:
                    self.wfile.write(
                        confFile.read().encode("utf-8")
                    )
            else:
                self.response404()
        elif self.command =="POST":
            self.response500()
        else:
            self.response501()

    def doRadarConfig(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write("Do radar config".encode("utf-8"))

    def doRadarTrialBurst(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write("Do trial burst".encode("utf-8"))

    def doRadarBurst(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write("Do radar burst".encode("utf-8"))

    def doDataDir(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write("Do data dir".encode("utf-8"))

    def doDataDownload(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write("Do data download".encode("utf-8"))

    def do_GET(self):
        self.handleAllRequests()

    def do_POST(self):
        # Validate authentication
        self.handleAllRequests()

    def handleAllRequests(self):
        
        # Split path
        spath = self.path.split("/")
        if len(spath) < 3:
            # Empty path
            self.do_404()
            return
        else:
            # Truncate to last two elements (as leading / will give '' in split array)
            spath = spath[1:]

        # Verify first element is api
        if spath[0].lower() != 'api':
            self.do_404()
            return

        # Iterate over path and validate
        mdict = self.API_ROUTES
        for cpath in spath[1:]:
            if cpath in mdict:
                if isinstance(mdict[cpath], dict):
                    mdict = mdict[cpath]
                elif isinstance(mdict[cpath], str):
                    # Call method
                    getattr(self, mdict[cpath])()
                    return
                else:
                    print(mdict[cpath])
            else:
                self.do_404()
                return

    def do_404(self):
        self.send_response(404)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write("Not Found".encode("utf-8"))