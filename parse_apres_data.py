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
            Reg01="000C0820" # 
            Reg02="0D1F41C8"
            Reg0B="0A3D70A4051EB852"
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