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
    #Load Modules
    heater_shaker = protocol.load_module('heaterShakerModuleV1', 'D1')

    # Load adapters
    hs = heater_shaker.load_adapter('opentrons_universal_flat_adapter')
    
    # Load labware
    hs_plate = hs.load_labware('deep_well_plate_with_universal_adapt', 'A2')

    #Move hs_plate onto heater shaker
    heater_shaker.open_labware_latch()
    protocol.move_labware(labware=hs_plate, new_location=heater_shaker, use_gripper=True)
    heater_shaker.close_labware_latch()



