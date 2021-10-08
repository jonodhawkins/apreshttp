import http.server
import datetime
import threading
import socketserver
import tempfile 

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

        self.serverThread = None
        self.running = False

    def start(self):
        if self.serverThread == None:
            self.running = True
            self.serverThread = threading.Thread(target=self.serve_until_stop).start()
        else:
            raise Exception("Server has already been started.")

    def stop(self):
        self.running = False

    def serve_until_stop(self):
        while self.running:
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

    apiRoutes = {
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

    def doSystemReset(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write("Do system reset".encode("utf-8"))

    def doHousekeepingStatus(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write("Do housekeeping status".encode("utf-8"))

    def doHousekeepingConfig(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write("Do housekeeping config".encode("utf-8"))

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
        mdict = self.apiRoutes
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

    def do_POST(self):
        pass

    def do_404(self):
        self.send_response(404)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write("Not Found".encode("utf-8"))