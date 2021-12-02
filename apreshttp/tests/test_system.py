import apreshttp.base as apreshttp # from . import base as apreshttp 

import os
import datetime
import pytest
import random
import tempfile

# API_ROOT = "http://localhost:8000" #"http://radar.localnet"
# API_ROOT = "http://radar.localnet"
API_ROOT = "http://192.168.1.1"
API_KEY = "18052021"
CONFIG_TEST_FILE = "config_test.ini"
CONFIG_UPLOAD_FILE_A = "apreshttp/tests/upload_config_a.ini"
CONFIG_UPLOAD_FILE_B = "apreshttp/tests/upload_config_b.ini"

def test_apichild_object():

    # Create API instance
    api = apreshttp.API(API_ROOT)
    # Check root matches
    assert api.root == API_ROOT

    # Try testing without preceeding http://
    api = apreshttp.API(API_ROOT[7:])
    # Check that http:// has been added
    assert api.root == API_ROOT

    # Try testing with preceeding whitespace
    api = apreshttp.API(hex(random.getrandbits(64))[2:] + API_ROOT)
    assert api.root == API_ROOT

    # Check APIChild URL formation
    apiChild = apreshttp.APIChild(api)
    TEST_URL = "system/reset"
    assert apiChild.formCompleteURL(TEST_URL) == (API_ROOT + "/api/" + TEST_URL)

    # Change APIChild root
    TEST_URL = "system/housekeeping/status"
    assert apiChild.formCompleteURL(TEST_URL) == (API_ROOT + "/api/" + TEST_URL)

def test_system_reset():

    # Create API instance
    api = apreshttp.API(API_ROOT)

    # Use invalid API key
    with pytest.raises(apreshttp.InvalidAPIKeyException):
        api.system.reset()
        # Try setting invalid key
        api.setKey("")

    # Check that an invalid key causes an exception
    with pytest.raises(apreshttp.InvalidAPIKeyException):
        api.setKey("InvalidKey")
        api.system.reset()

    # Try resetting
    api.setKey(API_KEY)
    response = api.system.reset()

    # Check that the response is a ResetMessage object
    assert isinstance(response, apreshttp.System.ResetMessage)
    # And that the components are string and datetime
    assert isinstance(response.message, str)
    assert isinstance(response.time, datetime.datetime)

def test_system_status():

    # Create API instance
    api = apreshttp.API(API_ROOT)

    status = api.system.housekeeping.status()
    assert isinstance(status, apreshttp.System.Housekeeping.Status)
    assert isinstance(status.batteryVoltage, int) or isinstance(status.batteryVoltage, float)
    assert status.timeGPS == None or isinstance(status.timeGPS, datetime.datetime)
    assert status.timeVAB == None or isinstance(status.timeVAB, datetime.datetime)
    assert isinstance(status.latitude, float) or isinstance(status.latitude, int)
    assert isinstance(status.longitude, float) or isinstance(status.longitude, int)

def test_system_housekeeping_config_get():

    # Create API instance
    api = apreshttp.API(API_ROOT)

    # If the local config file exists at the start of the test, delete it so we
    # can check it exists afterwards
    if os.path.isfile(CONFIG_TEST_FILE):
        os.remove(CONFIG_TEST_FILE)

    # Also check whether there is a "config.ini" and remove that
    if os.path.isfile("config.ini"):
        os.remove("config.ini")

    # First of all, try and download config.ini
    api.system.housekeeping.config.download()
    assert os.path.isfile("config.ini")
    # Clean up
    os.remove("config.ini")

    api.system.housekeeping.config.download(CONFIG_TEST_FILE);
    assert os.path.isfile(CONFIG_TEST_FILE)
    # Clean up
    os.remove(CONFIG_TEST_FILE)

def test_system_housekeeping_config_set():

    # Create API instance
    api = apreshttp.API(API_ROOT)

    tempDir = tempfile.TemporaryDirectory()
    filename = os.path.join(tempDir.name, hex(random.getrandbits(128))[2:] + ".ini")
    TO_UPLOAD = CONFIG_UPLOAD_FILE_A
    # Check which config file is onboard
    try:
        api.system.housekeeping.config.download(filename, True)

        # Read the config file first line
        with open(filename, 'r') as fh:
            line = fh.readline()
            # If it's file A, then up load B
            if line.find(";UPLOAD_CONFIG_A") > -1:
                TO_UPLOAD = CONFIG_UPLOAD_FILE_B
            # Otherwise we'll upload A

    except Exception:
        if os.path.isfile(filename):
            # If we didn't download the file for some reason then quit
            os.remove(filename)
            pytest.skip("Unable to download current config.ini, did the other test fail?")

    finally:
        if os.path.isfile(filename):
            os.remove(filename)

    # Try to upload config without authentication
    with pytest.raises(apreshttp.InvalidAPIKeyException):
        api.system.housekeeping.config.upload(TO_UPLOAD)

    # Now try with authentication
    api.setKey(API_KEY)
    api.system.housekeeping.config.upload(TO_UPLOAD)

    try:
        # Now we try downloading
        api.system.housekeeping.config.download(CONFIG_TEST_FILE)

        # Try reading file
        with open(CONFIG_TEST_FILE, 'r') as fh:
            line = fh.readline()
            # Check what we were uploading
            if TO_UPLOAD == CONFIG_UPLOAD_FILE_A:
                assert line.find(";UPLOAD_CONFIG_A") > -1
            else:
                assert line.find(";UPLOAD_CONFIG_B") > -1
    finally:
        if os.path.isfile(CONFIG_TEST_FILE):
            os.remove(CONFIG_TEST_FILE)
