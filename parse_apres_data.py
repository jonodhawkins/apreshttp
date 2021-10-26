import numpy as np
import os
import re
import sys
from matplotlib import pyplot as plt

if __name__ == "__main__":

    print("Found {nArg:d} arguments.".format(nArg=len(sys.argv)))

    filename = sys.argv[1]
    if not os.path.exists(filename):
        print("Invalid path")
        exit()
    else:

        print("Parsing {fname:s}".format(fname=filename))
        headerDict = dict()

        with open(filename, 'rb') as fh:
            
            # Try to find start of the header
            discardedLines = 0
            line = fh.readline().decode("utf-8")
            # Check not end of file and find start of header
            while len(line) > 0 and line.find("*** Burst Header ***") < 0:
                discardedLines += 1
                line = fh.readline().decode("utf-8")

            if len(line) == 0:
                print("Could not find start of header.  Check file.")
                exit()
            else:
                # Read next line as we are on *** Burst Header ***
                line = fh.readline().decode("utf-8")
                
            
            # Compile header regex
            pHeader = re.compile("([\w\s]+)=(.+)\s")
            nonWhitespace = re.compile("\S+")

            while len(line) > 0 and line.find("*** End Header ***") < 0:
                discardedLines += 1
                matchHeader = pHeader.match(line)
                
                if matchHeader != None:
                    headerDict[matchHeader.group(1)] = matchHeader.group(2)
                    
                    if matchHeader.group(2)[-1:] == "\r":
                        headerDict[matchHeader.group(1)] = matchHeader.group(2)[:-1]

                elif nonWhitespace.match(line) != None:
                    print("Error in header on line {lineNo:d} [len {len:d}]: {line:s}".format(len=len(line), lineNo = discardedLines, line=line))
                    exit()

                line = fh.readline().decode("utf-8")

            print(headerDict)
            print("Finished parsing header")

            # Parse registers

            Reg00="00000008" # External power down control
            # 0000 0000 0000 0000 0000 0000 0000 0000
            Reg01="000C0820" 
            # 0000 0000 0000 1100 0000 1000 0010 0000
            Reg02="0D1F41C8"
            # 0000 1101 0001 1111 0100 0001 1100 1000
            Reg0B="0A3D70A4051EB852"
            # 63:32 upper limit
            # 31:0 lower limit
            Reg0C="000006B6000006B6"
            Reg0D="13881388"
            Reg0E="08B5000000000000"

            #TODO: Calculate data to read
            # But for now let's just try reading 40000
            chirpBurst = int(headerDict["NSubBursts"])
            nAttn = int(headerDict["nAttenuators"])
            nSample = int(headerDict["N_ADC_SAMPLES"])

            print("Reading {nat:d} attenuator data with {nsb:d} sub bursts each".format(
                nat=chirpBurst,
                nsb=nAttn
            ))

            print("Reading data")

            for attn in range(nAttn):
                data = np.zeros(nSample, dtype=np.dtype("<u4"))
                for subburst in range(chirpBurst):
                    data = data + np.fromfile(fh, dtype=np.dtype("<u2"), count=nSample)
                plt.plot(data / (chirpBurst) * 2.5 / 2**16)

            print("Finished reading data at {tell:d}".format(tell=fh.tell()))
            plt.show()

def parseDDSRegisters(**kwargs):


    # Create dict for parsed data
    outputDict = dict()

    # 1 GHz internal PLL sysfreq?
    FREQ_SYS_CLK = 1e9

    RAMP_ENABLE            = 0x00080000
    RAMP_NO_DWELL_HIGH     = 0x00040000
    RAMP_NO_DWELL_LOW      = 0x00020000
    EXTERNAL_POWER_DOWN    = 0x00000008
    PDCLK_ENABLE           = 0x00000800
    TX_ENABLE_INVERT       = 0x00000200
    SYNC_TIMING_VALIDATION = 0x00000010
    DRIVE_REFCLK_OUT       = 0x30000000
    VC0_SELECT             = 0x07000000
    PLL_I_CHARGE_PUMP      = 0x00380000
    REFCLK_DIV_BYPASS      = 0x00008000
    REFCLK_DIV_RESET       = 0x00004000
    PFD_RESET              = 0x00000400
    REFCLK_PLL_ENABLE      = 0x00000100
    REFCLK_PLL_DIVIDER     = 0x000000FE



    if "Reg00" in kwargs:
        if len(kwargs["Reg00"]) == 16:
            Reg00 = int(kwargs["Reg00"], 16)
            outputDict["externalPowerDown"] = Reg00 & EXTERNAL_POWER_DOWN 
        else:
            raise Exception("Invalid DDS Reg00 length ({:d}), should be 16.".format(len(kwargs["Reg00"])))
    
    if "Reg01" in kwargs:
        if len(kwargs["Reg01"]) == 16:
            Reg01 = int(kwargs["Reg01"], 16)
            outputDict["rampEnable"] = Reg01 & RAMP_ENABLE
            outputDict["rampNoDwellHigh"] = Reg01 & RAMP_NO_DWELL_HIGH
            outputDict["rampNoDwellLow"] = Reg01 & RAMP_NO_DWELL_LOW

    if "Reg02" in kwargs:
        pass

    # Frequency limit
    if "Reg0B" in kwargs:
        if len(kwargs["Reg0B"]) == 16:
            outputDict["upperFrequencyLimit"] = int(kwargs["Reg0B"][0:7], 16) / (2**32) * FREQ_SYS_CLK
            outputDict["lowerFrequencyLimit"] = int(kwargs["Reg0B"][8:15], 16) / (2**32) * FREQ_SYS_CLK
        else:
            raise Exception("Invalid DDS Reg0B length.")

    # Frequency step
    if "Reg0C" in kwargs:
        if len(kwargs["Reg0C"]) == 16:
            outputDict["negativeFrequencyStep"] = int(kwargs["Reg0C"][0:7], 16) / (2**32) * FREQ_SYS_CLK
            outputDict["positiveFrequencyStep"] = int(kwargs["Reg0C"][8:15], 16) / (2**32) * FREQ_SYS_CLK
        else:
            raise Exception("Invalid DDS Reg0C length.")

    # Time step
    if "Reg0D" in kwargs:
        if len(kwargs["Reg0D"]) == 8:
            outputDict["negativeTimeStep"] = int(kwargs["Reg0D"][0:3], 16) / FREQ_SYS_CLK * 4
            outputDict["positiveTimeStep"] = int(kwargs["Reg0D"][4:7], 16) / FREQ_SYS_CLK * 4
        else:
            raise Exception("Invalid DDS Reg0D length.")

    if "Reg0E" in kwargs:
        pass
            # Reg00="00000008" # External power down control
            # # 0000 0000 0000 0000 0000 0000 0000 0000
            # Reg01="000C0820" 
            # # 0000 0000 0000 1100 0000 1000 0010 0000
            # Reg02="0D1F41C8"
            # # 0000 1101 0001 1111 0100 0001 1100 1000
            # Reg0B="0A3D70A4051EB852"
            # # 63:32 upper limit
            # # 31:0 lower limit
            # Reg0C="000006B6000006B6"
            # Reg0D="13881388"
            # Reg0E="08B5000000000000"