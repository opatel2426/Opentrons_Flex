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
    num_oligos = 4
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
    tips_200 = protocol.load_labware(load_name="opentrons_flex_96_filtertiprack_200ul",location="A3")
    plate1 = protocol.load_labware('opentrons_96_wellplate_200ul_pcr_full_skirt', 'B2')
    plate2 = protocol.load_labware('opentrons_96_wellplate_200ul_pcr_full_skirt', location='C2')

    # Liquid definitions
    digested_plasmid = protocol.define_liquid(name = 'Digested Plasmid', display_color="#704848",)
    ddH2O = protocol.define_liquid(name = 'ddH2O', display_color="#5248D8",)
    T4_LB = protocol.define_liquid(name = '10X T4 Ligation Buffer', display_color="#48D89E",)
    T4_PNK = protocol.define_liquid(name = 'T4 PNK', display_color="#D84876",)
    QL_buffer = protocol.define_liquid(name = '2X Quick ligase Buffer', display_color="#710000",)
    QL = protocol.define_liquid(name = 'Quick Ligase', display_color="#B2D848",)
    SOC_media = protocol.define_liquid(name = 'SOC media', display_color="#48CCD8",) #have to control temp

    # Temp adapter assignments for washes and digestion
    temp_adapter['A1'].load_liquid(liquid=digested_plasmid, volume = 1500)
    temp_adapter['A2'].load_liquid(liquid=ddH2O, volume = 1500)
    temp_adapter['A3'].load_liquid(liquid=T4_LB, volume = 1500)
    temp_adapter['A4'].load_liquid(liquid=T4_PNK, volume = 1500)
    temp_adapter['A5'].load_liquid(liquid=QL_buffer, volume = 1500)
    temp_adapter['A6'].load_liquid(liquid=QL, volume = 1500)

    #assign oligo locations dynamically (They are in pairs since forward and reverse primers have to be separated)
    oligo_locations = []
    for i in range(num_oligos):
        if i < 6:  # B1 to B6
            oligo_locations.append(f'B{i + 1}')
        elif i < 12:  # C1 to C6
            oligo_locations.append(f'C{i - 5}')
        elif i < 18:  # D1 to D6
            oligo_locations.append(f'D{i - 11}')
        else:
            break  # Stop if we exceed the number of available rows/columns


    #Load pipettes
    p50_multi = protocol.load_instrument('flex_8channel_50', 'left') 
    p1000_multi = protocol.load_instrument('flex_8channel_1000', 'right') 

    #Step 1: Configure the p50 pipette to use single tip
    p50_multi.configure_nozzle_layout(style=SINGLE, start="A1",tip_racks=[partial_50])

    #Step 2: Pipette oligos into PCR plate for annealing
    p50_multi.distribute(6.5, #ddH2O
        temp_adapter['A2'],
        [plate1[i+1].bottom(z=0.3) for i in range(num_oligos/2)],
        rate = speed)
    
    p50_multi.distribute(1, #T4_LB
        temp_adapter['A3'],
        [plate1[i+1].bottom(z=0.3) for i in range(num_oligos/2)],
        rate = speed,
        new_tip = 'always')
    
    p50_multi.distribute(0.5, #T4_PNK
        temp_adapter['A4'],
        [plate1[i+1].bottom(z=0.3) for i in range(num_oligos/2)],
        rate = speed,
        new_tip = 'always')
    
    # Predefined list of letters A-H
    row = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']

    # Create a list of rows that repeats based on num_oligos
    rows = [row[i % len(row)] for i in range(num_oligos/2)]

    # Create a dynamic sample map based on the assigned oligo locations
    sample_map = list(map(lambda i,j :(i,j), rows, oligo_locations))

    # Iterate over the sample_map list
    for index, (row, tube) in enumerate(sample_map):
        if index < 8:
            base_column = 4 + (index // 8)  # This will determine the starting column for each row
        elif index< 16:
            base_column = 6 + (index // 8)
        else:
            base_column = 8 + (index //8)

        # Prepare destination wells
        destination_wells = [f'{row}{base_column + (i % 3)}' for i in range(3)]  # Generate wells like A4, A5, A6 or B4, B5, B6, etc.
        
        #Transfer the oligos onto plate 1
        p50_multi.distribute(1,
                        temp_adapter[tube],
                        [plate1[i].bottom(z=0.3) for i in destination_wells],
                        rate = speed,
                        mix_before=(1, 8))  # Distributing to three consecutive columns

    #Anneal the oligos
    thermocycler.open_lid()
    protocol.move_labware(labware=plate1, new_location=thermocycler, use_gripper=True)
    thermocycler.close_lid()
    thermocycler.set_block_temperature(37,hold_time_minutes=30)
    
    #Prepare annealing temperatures
    x = 95
    thermocycler.set_block_temperature(x)
    protocol.delay(minutes=5)

    cycles = 14 #set how many cycles needed to decrease temperature 
    for i in range(cycles*5):
        x = x - 1
        thermocycler.set_block_temperature(x,
        hold_time_seconds=12)