from opentrons import protocol_api
from opentrons.protocol_api import SINGLE, ALL
import pandas as pd
import numpy as np
import subprocess
from pathlib import Path
import datetime
import time


metadata = {
    'protocolName': 'Annealing gRNA',
    'author': 'Assistant',
    'description': 'Serial dilution of BSA standard and sample processing. This includes cooling samples to 4c, heating plate to 37c with shaking and recording a video of the whole process. Place BSA Standard in A1, Lysis buffer in A2, change the number of samples and place samples in row B starting at B1. MINIMUM Sample volumen in eppendorf tubes is 40 uL. '
}

requirements = {
    "robotType": "Flex",
    "apiLevel": "2.21"
}


def run(protocol: protocol_api.ProtocolContext):
    #Load Thermocycler
    thermocycler = protocol.load_module('thermocyclerModuleV2')
    thermocycler.set_block_temperature(37)
    protocol.delay(minutes=30)

    x = 95
    thermocycler.set_block_temperature(x)
    protocol.delay(minutes=5)

    cycles = 14 #set how many cycles needed to decrease temperature 
    for i in range(cycles*5):
        x = x - 1
        thermocycler.set_block_temperature(x,
        hold_time_seconds=12)