# Demonstrate Capacbilities of apreshttp API
import apreshttp.base as apreshttp
import os
import requests
import tkinter as tk
import numpy as np
from tkinter import messagebox as mb

from matplotlib import pyplot as plt

# API 
api = apreshttp.API("http://radar.localnet")
api.setKey("18052021")

# Get radar status 
print("Reading radar status")
try:
    status = api.system.housekeeping.status()

    # Print out status values
    print("Battery Voltage : {}".format(status.batteryVoltage))
    print("GPS Lat.        : {}".format(status.latitude))
    print("GPS Long.       : {}".format(status.longitude))
    print("Time GPS        : {}".format(status.timeGPS))
    print("Time VAB        : {}".format(status.timeVAB))

except requests.exceptions.ConnectionError:
    print("ERROR: Unable to connect to radar. Quitting...")
    exit()

except apreshttp.BadResponseException:
    print("ERROR: Unable to read status. Quitting...")
    exit()

# Define user settings
natts = 1
naverages = 1

natts = int(input("Enter the number of attenuator settings [1-4]: "))
if natts < 0 or natts > 4:
    natts = 1
    print("WARNING: Defaulting to 1 attenuator setting.")

naverages = int(input("Enter the number of averages per trial burst [>= 1]: "))
if naverages < 1:
    naverages = 1
    print("WARNING: Defaulting to 1 average.")

rfAttnSet = []
afGainSet = []

for attn in range(natts):
    print("Settings for attenuator #{}".format(attn+1))
    print("--------------------------")
    
    rf = float(input("    Enter the RF attenuation [0-31]: "))
    if rf < 0 or rf > 31:
        rf = 30
        print("    WARNING: Defaulting to RF attenuator of 30dB")
    rfAttnSet.append(rf)

    af = int(input("    Enter the RF attenuation [-14, -4, 6]: "))
    if af != -14 and af != -4 and af != 6:
        af = -4
        print("    WARNING: Defaulting to AF gain of -4 dB")
    afGainSet.append(af)

print("Updating config.")
api.radar.config.set(
    nAtts=natts,
    nAverages=naverages,
    nBursts=naverages,
    rfAttnSet=rfAttnSet,
    afGainSet=afGainSet
)

print("Peforming trial burst")
try:
    api.radar.trialBurst()
except (apreshttp.RadarBusyException, apreshttp.NoChirpStartedException):
    print("ERROR: Could not start chirp, quitting.")
    exit()

# Create update callback function to show progress
def updateCallback(response):
    print(".")

print("Waiting for results")
results = api.radar.results(wait = True, updateCallback=updateCallback)

print("Plotting results...")
fig, axs = plt.subplots(1, 2)
for at in range(results.nAttenuators):
    axs[0].bar(np.linspace(0,2.5,len(results.histogram[at])), results.histogram[at],  alpha = 0.5, width=2.5/len(results.histogram[at]))
    axs[1].plot(results.chirp[at])
    
axs[0].set_xlabel("Voltage (V)")
axs[0].set_ylabel("Count")
axs[0].set_title("Histogram")

axs[1].set_xlabel("Sample No.")
axs[1].set_ylabel("Voltage (V)")
axs[1].set_title("Deramped Signal")

plt.show()

