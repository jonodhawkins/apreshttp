import apreshttp.base as apreshttp

import datetime
import matplotlib.pyplot as plt
import pytest
import random

# API_ROOT = "http://localhost:8000" # "http://radar.localnet"
# API_ROOT = "http://radar.localnet"
API_ROOT = "http://192.168.1.1"
API_KEY = "18052021"

def test_radar_config_get():

    api = apreshttp.API(API_ROOT)

    config = api.radar.config.get()

    # Check members have been assigned
    assert config.nAttenuators != None
    assert config.nSubBursts != None
    assert len(config.afGain) > 0
    assert len(config.rfAttn) > 0
    assert isinstance(config.userData, str)

def test_radar_config_set():

    api = apreshttp.API(API_ROOT)

    # Check that we fail if no API key is provided
    with pytest.raises(apreshttp.InvalidAPIKeyException):
        config = api.radar.config.set(nAtts = 3)

    # Set API key
    api.setKey(API_KEY)

    # Try various config setups
    config = api.radar.config.set(nAtts = 3)
    assert config.nAttenuators == 3
    config = api.radar.config.set(nAtts = 2, nBursts = 5)
    assert config.nSubBursts == 5
    assert config.nAttenuators == 2

    # Set array fo AF and RF values
    rfValues = {
        'rfAttn1' : 13,
        'rfAttn2' : 19.5,
        'rfAttn3' : 12.5,
        'rfAttn4' : 9.0
    }

    afValues = {
        'afGain1' : -14,
        'afGain2' : -4,
        'afGain3' : 6,
        'afGain4' : -14
    }

    # Try various rfAttn and afGain settings
    config = api.radar.config.set(
        nAtts = 4,
        rfAttnSet = rfValues,
        afGainSet = afValues
    )

    for i in range(len(config.afGain)):
        assert config.afGain[i] == list(afValues.values())[i]

    for i in range(len(config.rfAttn)):
        assert config.rfAttn[i] == list(rfValues.values())[i]

    stateVarTemp = hex(random.getrandbits(32))[2:];
    config = api.radar.config.set(userData=stateVarTemp)

    assert config.userData == stateVarTemp

    api.radar.config.set(userData="")

    with pytest.raises(KeyError):
        # Try to set 4th attenuator value when only 3 are enabled
        config = api.radar.config.set(nAtts = 3, rfAttnSet = {'rfAttn4':20})
        
    # Need to succesfully update nAtts to 3 for the next test to work
    config = api.radar.config.set(nAtts = 3)

    with pytest.raises(KeyError):
        # Try to set 4th gain when only 3 are enabled
        config = api.radar.config.set(afGainSet = {'afGain4':6})

    with pytest.raises(ValueError):
        # Try to do the same but with list argument
        config = api.radar.config.set(nAtts = 2, rfAttnSet = [10,20,30])
    
    # Again, need to set the attenuators to 2
    config = api.radar.config.set(nAtts = 2)

    with pytest.raises(ValueError):
        # Try to set the 3rd gain when nAtts = 2
        config = api.radar.config.set(afGainSet = [-14,-4,6])
        
    with pytest.raises(ValueError):
        # Using a list, only provide 2 out of 3 attenuation values
        config = api.radar.config.set(nAtts = 3, rfAttnSet = [10,20])#
        
    # Update nAtts to 3
    config = api.radar.config.set(nAtts = 3)
        
    with pytest.raises(ValueError):
        # Try setting afGain using a list
        config = api.radar.config.set(nAtts = 3, afGainSet = [-14,-4])
        
    with pytest.raises(ValueError):
        # nAtts should be 3, so these should fail
        config = api.radar.config.set(rfAttnSet = 9)
        
    with pytest.raises(ValueError):
        config = api.radar.config.set(afGainSet = -4)

    # Try Tx and Rx antenna setting
    # Choose two random between 1 and 255
    randTxInt = random.getrandbits(8)
    randTx = tuple([int((randTxInt & 2**x) >> x) for x in range(8)])
    randRxInt = random.getrandbits(8)
    randRx = tuple([int((randRxInt & 2**x) >> x) for x in range(8)])

    config = api.radar.config.set(txAnt = randTx, rxAnt = randRx)
    
    assert config.txAntenna == randTx
    assert config.rxAntenna == randRx

    with pytest.raises(ValueError):
        api.radar.config.set(txAnt=(0,0,0))
    
    with pytest.raises(ValueError):
        api.radar.config.set(txAnt=[0,0,0,0,0,0,0,0])

def test_radar_trial_burst():

    # Create an API instance
    api = apreshttp.API(API_ROOT)
    api.setKey(API_KEY)

    # Try to perform a trial burst
    api.radar.trialBurst(wait=False)
    print("Done first trial")
    with pytest.raises(apreshttp.RadarBusyException):
        print("Try error trial")
        api.radar.trialBurst()

    api.radar.results()

def test_radar_trial_burst_callback():

    # Create an API instance
    api = apreshttp.API(API_ROOT)
    api.setKey(API_KEY)

    config = api.radar.config.set(nAtts=3, rfAttnSet={'rfAttn1':10,'rfAttn2':20,'rfAttn3':30}, afGainSet=[6, 6, 6])

    print(config.nAttenuators)
    print(config.rfAttn[0])
    print(config.rfAttn[1])
    print(config.rfAttn[2])

    tcallback = TestCallback();

    api.radar.trialBurst(tcallback.setResponse, wait=True)

    # tcallback.plot()

class TestCallback:

    def __init__(self):
        self.response = None

    def setResponse(self, resp):
        self.response = resp

    def update(self, resp):
        rjson = resp.json()
        msg = rjson["status"]
        if "chirpNumber" in rjson:
            msg += " " + str(rjson["chirpNumber"])
        print(msg)

    def plot(self):
        fig, axs = plt.subplots(1, 2)
        for at in range(self.response.nAttenuators):
            axs[0].bar(range(len(self.response.histogram[at])), self.response.histogram[at],  alpha = 0.5)
            axs[1].plot(self.response.chirp[at])
        plt.show()

def test_radar_burst():

    # Create an API instance
    api = apreshttp.API(API_ROOT)

    api.setKey(API_KEY)
    
    api.radar.config.set(nAtts = 1, nBursts = 5, rfAttnSet=10, afGainSet=6, txAnt=(1,0,0,0,0,0,0,0), rxAnt=(1,0,0,0,0,0,0,0));

    api.setKey("INVALID KEY")

    # Test burst doesn't go ahead
    with pytest.raises(apreshttp.InvalidAPIKeyException):
        api.radar.burst()

    api.setKey(API_KEY)

    # Perform a burst using an unknown filename
    api.radar.burst()
    
    # Create callback object
    cb = TestCallback()

    # Get results
    api.radar.results(cb.setResponse, updateCallback = cb.update, wait=True)

    # Validate filename
    assert isinstance(cb.response.filename, str)
    print(cb.response.filename)

    # Create variable for filename
    filename = datetime.datetime.now().strftime("%Y%m%d_%H-%M-%S") + ".dat"

    api.radar.burst(filename)

    api.radar.results(cb.setResponse, wait=True)

    # Check that the filenames match
    assert cb.response.filename == "Survey/"+filename

    # Try again - should get an error
    with pytest.raises(apreshttp.RadarBusyException):
        api.radar.burst(filename) 

