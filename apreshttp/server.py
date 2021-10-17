import cgi
import csv
import datetime
import http.server
import http.client
import json
import os
import re
import tempfile 
import threading
import urllib.parse
import importlib.resources
from requests_toolbelt.multipart import decoder as multipart_decoder
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
        self.afGain = [-4,]
        self.rfAttn = [0,]
        self.nAttenuators = 1
        self.nSubBursts = 1
        self.nAverages = 1
        self.startFrequency = 2e8
        self.stopFrequency = 4e8
        self.period = 1
        self.userData = ""
        self.txAntenna = [1,]
        self.rxAntenna = [1,]

        # Create temporary directory
        if localFolder == None:
            self.tempDir = tempfile.TemporaryDirectory()
            self.localFolder = self.tempDir.name
        else:
            self.tempDir = None
            self.localFolder = localFolder

        self.lastFile = None

        # Check if there is a config file in the local folder
        self.configPath = os.path.join(self.localFolder, "config.ini")
        if not os.path.exists(self.configPath):
            with open(self.configPath, 'w+') as confHandle:
                confHandle.write(importlib.resources.read_text('apreshttp.tests', 'upload_config_a.ini')) 
        # Also create a data_files path to be used for the test data
        self.dataPath = os.path.join(self.localFolder, "data_files")
        if not os.path.exists(self.dataPath):
            print("Creating data_files directory at {path:s}".format(path=self.dataPath))
            os.mkdir(self.dataPath)
        print("Found {count:d} files in data_files.".format(count=len(os.listdir(self.dataPath))))
        if len(os.listdir(self.dataPath)) < 1:
            with open(os.path.join(self.dataPath, "sample-apres-data.dat"), 'wb') as fh:
                fh.write(importlib.resources.read_binary("apreshttp", "sample-apres-data.dat"))

        self.serverThread = None
        self.running = False

        self.state = "idle"
        self.burstType = None
        self.startBurstTime = None

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

    def isBursting(self):
        return self.state == "burst" or self.state == "trial-burst" 

    def startTrialBurst(self):
        self.state = "trial-burst"
        self.burstType = "trial"
        self.startBurstTime = datetime.datetime.now()

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

    FIND_DIGIT_RE = re.compile("(\d+)")

    API_KEY = 18052021

    def authenticatePostRequest(self):
        content_len = int(self.headers.get('content-length'))
        self.contentType, pdict = cgi.parse_header(self.headers.get('content-type'))
                
        print("Authenticating {ct:s}".format(ct=self.contentType))
        self.responseBody = self.rfile.read(content_len)

        # Check request typee
        if self.contentType.lower() == "multipart/form-data":
            # parsed_data = cgi.parse_multipart(bytes(post_body), pdict)
            pname = re.compile("name=\"apikey\"")

            for part in multipart_decoder.MultipartDecoder(self.responseBody, self.headers.get('content-type')).parts:
                print(part.headers)
                for key in part.headers:
                    if key.decode("utf-8").lower() == "content-disposition":
                        nameMatch = pname.search(part.headers[key].decode('utf-8'))
                        if nameMatch:
                            print(part.content.decode('utf-8'))
                            return part.content.decode('utf-8') == str(self.API_KEY)
                    # if key.decode('utf-8') == 'apikey' and part.headers[key].decode('utf-8') == str(self.API_KEY):
                    #     return True
                    # else:
                    #     continue
            return False

        elif self.contentType.lower() == "application/x-www-form-urlencoded":
            parsed_data = urllib.parse.parse_qs(self.responseBody.decode('utf-8'))
            return 'apikey' in parsed_data and str(parsed_data['apikey'][0]) == str(self.API_KEY)
        else:
            return False
        # Need to encode the response as ASCII before parsing to avoid 
        # byte data out
        
        # This could be tidied up - check that there is actually a value
        # in ['apikey'] before calling ['apikey'][0]

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
                "longitude" : 0.0,
                "localFolder" : self.server.localFolder
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
            if not self.authenticatePostRequest():
                self.response401()
            else:
                print(self.contentType)
                if self.contentType == "multipart/form-data":

                    print("Doing housekeeping config multipart") 
                    pname = re.compile("name=\"([^\"]*)\"")
                    pfilename = re.compile("filename=\"([^\"]*)\"")

                    for part in multipart_decoder.MultipartDecoder(self.responseBody, self.headers.get('content-type')).parts:
                        for key in part.headers:
                            print(part.headers[key].decode("utf-8"))
                            fnameMatch = pfilename.search(part.headers[key].decode('utf-8'))
                            print(fnameMatch)
                            if fnameMatch:
                                print("Updating config")
                                # Path to config
                                pathToConfig = os.path.join(self.server.localFolder, "config.ini")
                                with open(pathToConfig, 'w') as fhConfig:
                                    fhConfig.write(part.content.decode('utf-8'))

                                print("Updated config")
                                self.send_response(201)
                                self.send_header("content-type","text/plain")
                                self.end_headers()
                                self.wfile.write(part.content)
                                return
                    
                self.responseError(400, 'No file uploaded.')

        else:
            self.response501()

    def doRadarConfig(self):
        if self.command == "GET":
            self.responseJSON(200, {
                "rfAttn" : self.server.rfAttn,
                "afGain" : self.server.afGain,
                "nSubBursts" : self.server.nSubBursts,
                "nAttenuators" : self.server.nAttenuators,
                "nAverages" : self.server.nAverages,
                "txAntenna" : self.server.txAntenna,
                "rxAntenna" : self.server.rxAntenna,
                "userData" : self.server.userData 
            })
        elif self.command == "POST":
            if not self.authenticatePostRequest():
                self.response401()
            else:
                if self.contentType == "application/x-www-form-urlencoded":
                    parsed_data = urllib.parse.parse_qs(self.responseBody.decode('utf-8'))
                    for key in parsed_data:
                        keylow = key.lower()
                        if keylow == "nattenuators":
                            nAttn = int(parsed_data[key][0])
                            if nAttn > 0 and nAttn < 5:
                                self.server.nAttenuators = nAttn
                            else:
                                self.responseError(400, "nAttenuators should be integer in range [1, 4]")
                                return
                        elif keylow == "nsubbursts":
                            nSubBurst = int(parsed_data[key][0])
                            if nSubBurst > 0:
                                self.server.nSubBursts = nSubBurst
                            else:
                                self.responseError(400, "nSubBursts should be integer greater than or equal to 1")
                                return
                        elif keylow == "naverages":
                            nAvg = int(parsed_data[key][0])
                            if nAvg > 0:
                                self.server.nAverages = nAvg
                            else:
                                self.responseError(400, "nAverages should be integer greater than or equal to 1")    
                                return
                        elif keylow == "txantenna":
                            try:
                                txStr = csv.reader(parsed_data[key])
                                # Cast to integer list
                                txList = [int(tx) for tx in list(txStr)[0]]
                                if any(v > 1 or v < 0 for v in txList):
                                    self.responseError(400, "txAntenna values should be 1 or 0")
                                self.server.txAntenna = txList
                            except Exception:
                                self.responseError(400, "Invalid txAntenna argument.  Should be in CSV format")
                        elif keylow == "rxantenna":
                            try:
                                rxStr = csv.reader(parsed_data[key])
                                # Cast to integer list
                                rxList = [int(rx) for rx in list(rxStr)[0]]
                                if any(v > 1 or v < 0 for v in rxList):
                                    self.responseError(400, "rxAntenna values should be 1 or 0")
                                self.server.rxAntenna = rxList
                            except Exception:
                                self.responseError(400, "Invalid txAntenna argument.  Should be in CSV format")
                        elif keylow == "userdata":
                            self.server.userData = str(parsed_data[key][0])

                    newRfAttn = []
                    newAfGain = []
                
                    for n in range(self.server.nAttenuators):
                        key = "rfAttn{idx:d}".format(idx=n+1) 
                        if key in parsed_data:
                            rfAttnValue = float(parsed_data[key][0])
                            newRfAttn.append(rfAttnValue)
                        else:
                            if n < len(self.server.rfAttn):
                                newRfAttn.append(self.server.rfAttn[n])
                            else:
                                newRfAttn.append(31.0)
                        
                        key = "afGain{idx:d}".format(idx=n+1)     
                        if key in parsed_data:
                            afGainValue = int(parsed_data[key][0])
                            newAfGain.append(afGainValue)
                        else:
                            if n < len(self.server.afGain):
                                newAfGain.append(self.server.afGain[n])
                            else:
                                newAfGain.append(-14)
                    
                    self.server.rfAttn = newRfAttn
                    self.server.afGain = newAfGain

                    # Bit of a hacky way to replicate the get behaviour
                    self.command = "GET"
                    self.doRadarConfig()

    def doRadarTrialBurst(self):
        if self.command == "POST":
            if not self.authenticatePostRequest():
                self.response401()
            else:
                if len(os.listdir(self.server.dataPath)) < 1:
                    self.responseError(500, "No data (*.dat) files found in data_files directory.")
                else:

                    if self.server.isBursting():
                        self.responseError(403, "Radar is already bursting")
                    else:

                        fileList = os.listdir(self.server.dataPath)
                        fileList.sort(key=self.fileSort)
                        if self.server.lastFile == None:
                            self.server.lastFile = fileList[0]
                        else:
                            # Increment to next file
                            idx = fileList.index(self.server.lastFile)
                            idx = (idx + 1) % len(fileList)
                            self.server.lastFile = fileList[idx]
                        
                        self.server.startTrialBurst()

                        self.send_response(303)
                        self.send_header("Location", "api/radar/results")
                        self.end_headers()

        else:
            self.responseError(403, "Cannot start trial burst using a GET request.")

    def fileSort(self, str_name):
        m = self.FIND_DIGIT_RE.findall(str_name)
        if m == None:
            return -1 
        else:
            return sum([float(m[i])*10**(len(m)-i-len(m[i])) for i in range(len(m))])

    def doRadarResults(self):
        if self.server.state == "trial-burst":

            # Calculate time delta
            td = datetime.datetime.now() - self.server.startBurstTime
            # Create response dictionary

            if td >= datetime.timedelta(seconds=self.server.nAverages * self.server.nAttenuators):
                self.server.state = "finished"

            self.responseJSON(200, {"status":"chirping","type":"trial"})

        elif self.server.state == "finished":

                # We need to load the next file from our dummy set and load the data

                responseDict = {
                    # present for all results
                    "status"        : "finished",
                    "type"          : self.server.burstType,
                    "nAttenuators"  : self.server.nAttenuators,
                    "rfAttn"        : self.server.rfAttn,
                    "afGain"        : self.server.afGain,
                    "startFrequency": self.server.startFrequency,
                    "stopFrequency" : self.server.stopFrequency,
                    "period"        : self.server.period
                }

                if self.server.burstType == "trial":
                    # present for trial burst results only
                    responseDict["histogram"] = [[0,]*self.server.nAttenuators]
                    responseDict["chirp"] = [[0,]*self.server.nAttenuators]
                    responseDict["nAverages"] = self.server.nAverages
                elif self.server.burstType == "burst":
                    responseDict["nSubBursts"] = self.server.nSubBursts
                    responseDict["filename"] = self.server.lastFile # TODO: Change this to be an auto generated name

                self.responseJSON(200, responseDict)
                
        else:
            self.responseJSON(200, {"status":"idle"})

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
                self.do_404()
                return

    def do_404(self):
        self.send_response(404)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write("Not Found".encode("utf-8"))

class PseudoResponse:

    def __init__(self, header, resp):
        self.headers = header
        self.content = resp

if __name__ == "__main__":
    srv = Server()
    srv.start()
    try:
        while True:
            pass
    except KeyboardInterrupt:
        srv.stop()
    