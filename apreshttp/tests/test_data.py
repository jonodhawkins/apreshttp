import apreshttp.base as apreshttp

import os
import random

API_ROOT = "http://radar.localnet"
API_KEY = "18052021"

def test_data_list():

    api = apreshttp.API(API_ROOT)
    api.setKey(API_KEY)

    # Try getting root
    listing = api.data.dir()

    assert isinstance(listing, apreshttp.Data.DirectoryListing)
    assert (len(listing.files) + len(listing.directories)) == listing.numObjectsInList
    print(listing.path)

    # Try getting the survey directory
    listing = api.data.dir("Survey")

    assert isinstance(listing, apreshttp.Data.DirectoryListing)
    assert (len(listing.files) + len(listing.directories)) == listing.numObjectsInList
    assert listing.path == "Survey"

    # Try getting another page
    if listing.numObjectsInList < listing.numObjectsInDir:
        listing2 = api.data.dir("Survey", 16)
        assert listing.files[0].name != listing2.files[0].name

def test_data_download():

    api = apreshttp.API(API_ROOT)
    api.setKey(API_KEY)

    try:
        api.data.download("config.ini")

        assert os.path.exists("config.ini")

    finally:
        if os.path.isfile("config.ini"):
            os.remove("config.ini")
            
    assert not os.path.exists("config.ini")

    filename = hex(random.getrandbits(128))[2:] + ".ini"

    try:
        api.data.download("config.ini", filename)

        assert os.path.exists(filename)

    finally:
        if os.path.isfile(filename):
            os.remove(filename)