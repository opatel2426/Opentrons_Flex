from opentrons import protocol_api
from opentrons.protocol_api import SINGLE, ALL
import pandas as pd
import numpy as np
import subprocess
from pathlib import Path
import datetime
import time

metadata = {
    'protocolName': 'Plasmid DNA Purification',
    'author': 'Assistant',
    'description': 'Serial dilution of BSA standard and sample processing. This includes cooling samples to 4c, heating plate to 37c with shaking and recording a video of the whole process. Place BSA Standard in A1, Lysis buffer in A2, change the number of samples and place samples in row B starting at B1. MINIMUM Sample volumen in eppendorf tubes is 40 uL. '
}

requirements = {
    "robotType": "Flex",
    "apiLevel": "2.21"
}

def run(protocol: protocol_api.ProtocolContext):
    protocol.comment("Performing plasmid DNA purification")
    num_samples = 10
    num_replicates = 2
    speed = 0.2

    #Start recording the video
    video_process = subprocess.Popen(["python3", "/var/lib/jupyter/notebooks/record_video.py"])

    #Load modules
    heater_shaker = protocol.load_module('heaterShakerModuleV1', 'D1')
    thermocycler = protocol.load_module('thermocyclerModuleV2')
    temp_module = protocol.load_module('temperature module gen2', 'C1')
    mag_block = protocol.load_module('magneticBlockV1', 'D2')
    chute = protocol.load_waste_chute()

    #Load adapters
    temp_adapter = temp_module.load_labware('opentrons_24_aluminumblock_nest_1.5ml_screwcap')

    #open heater_shaker
    heater_shaker.open_labware_latch()

    #set the temp module to 10c
    temp_module.set_temperature(celsius=10)

    # Load labware
    partial_50 = protocol.load_labware(load_name="opentrons_flex_96_filtertiprack_50ul",location="B3")
    plate1 = protocol.load_labware('opentrons_96_wellplate_200ul_pcr_full_skirt', 'B2')

    # Liquid definitions
    digested_plasmid = protocol.define_liquid(name = 'Digested Plasmid', display_color="#704848",)


    # Reservoir assignments for washes and digestion
    temp_adapter['A1'].load_liquid(liquid=digested_plasmid, volume = 1500)
    temp_adapter['A2'].load_liquid(liquid=digested_plasmid, volume = 1500)

    #Load pipettes
    p50_multi = protocol.load_instrument('flex_8channel_50', 'left') 
    p1000_multi = protocol.load_instrument('flex_8channel_1000', 'right') 

    #Anneal the oligos
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