from opentrons import protocol_api
from opentrons.protocol_api import SINGLE, ALL
import pandas as pd
import numpy as np
import subprocess
from pathlib import Path
import datetime
import time

metadata = {
    'protocolName': 'Test hs_plate',
    'author': 'Assistant',
    'description': 'Serial dilution of BSA standard and sample processing. This includes cooling samples to 4c, heating plate to 37c with shaking and recording a video of the whole process. Place BSA Standard in A1, Lysis buffer in A2, change the number of samples and place samples in row B starting at B1. MINIMUM Sample volumen in eppendorf tubes is 40 uL. '
}

requirements = {
    "robotType": "Flex",
    "apiLevel": "2.21"
}

def run(protocol: protocol_api.ProtocolContext):
    # Load adapters
    #hs_adapter = heater_shaker.load_adapter('opentrons_universal_flat_adapter')

    #Load Modules
    heater_shaker = protocol.load_module('heaterShakerModuleV1', 'D1')
    
    # Load labware
    hs_plate = protocol.load_labware('opentrons_96_wellplate_200ul_pcr_full_skirt', 'A2')

    #Move hs_plate onto heater shaker
    protocol.move_labware(labware=hs_plate, new_location=heater_shaker, use_gripper=True) 



