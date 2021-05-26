from .context import apreshttp

import os
import datetime
import pytest
import random

API_ROOT = "http://radar.localnet"
API_KEY = "18052021"

def test_radar_config_get():

    api = apreshttp.API(API_ROOT)

    config = api.radar.config.get()
