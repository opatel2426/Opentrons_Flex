from opentrons import protocol_api
from opentrons.protocol_api import SINGLE, ALL
import pandas as pd
import numpy as np
import subprocess
from pathlib import Path
import datetime
import time

metadata = {
    'protocolName': 'Gel-based Chemical Proteomics 08192025',
    'author': 'Om Patel and Thomas Hanigan',
    'description': 'BCA assay, followed by sample normalization, click reaction, and denaturation for Gel-based photolabeling.'
}

requirements = {
    "robotType": "Flex",
    "apiLevel": "2.21"
}

def add_parameters(parameters):

    parameters.add_int(
        variable_name="num_samples",
        display_name="Number of samples",
        description="Number of input samples to be tested for mycoplasma.",
        default=10,
        minimum=1,
        maximum=24
    )
    parameters.add_int(
        variable_name="standards_col",
        display_name="standards column",
        description="Integer of column on plate1 where standards will be diluted",
        default=1,
        minimum=1,
        maximum=12
    )
    parameters.add_float(
        variable_name="target_concentration",
        display_name="Target protein concentration",
        description="Concentration of normalized lysate in click reaction",
        default=1.5,
        minimum=1,
        maximum=2.5,
        unit="µg/µL"
    )

    parameters.add_int(
        variable_name="final_volume",
        display_name="final volume lysate",
        description="Volume to normalize µg of protein in",
        default=50,
        minimum=50,
        maximum=500,
        unit="µL"
    )
def run(protocol: protocol_api.ProtocolContext):
    protocol.comment(
        "Place BSA Standard in A1, Lysis buffer in A2, tbta in A3, biotin in A4, cuso4 in A5, tcep in A6 and samples in row B")
    protocol.comment("Running the BCA assay")
    num_rows = 8  # A-H
    speed= 0.3 #Speed of pipetting NP40 lysis buffer=0.35, 2M Urea in EPPS=0.3

    #Start recording the video
    video_process = subprocess.Popen(["python3", "/var/lib/jupyter/notebooks/record_video_chemprot.py"])

    # Load modules
    heater_shaker = protocol.load_module('heaterShakerModuleV1', 'D1')
    thermocycler = protocol.load_module('thermocyclerModuleV2')
    temp_module = protocol.load_module('temperature module gen2', 'C1')
    mag_block = protocol.load_module('magneticBlockV1', 'D2')
    chute = protocol.load_waste_chute()

    # Load adapters
    temp_adapter = temp_module.load_labware('opentrons_24_aluminumblock_nest_1.5ml_screwcap')

    #set the heater_shaker temp to 60C
    heater_shaker.open_labware_latch()

    #set the temp module to 0c
    temp_module.set_temperature(celsius=10)
    
    # Load labware
    partial_50 = protocol.load_labware(load_name="opentrons_flex_96_filtertiprack_50ul",location="B3")
    tips_200 = protocol.load_labware(load_name="opentrons_flex_96_filtertiprack_200ul",location="A3")
    tips_1000 = protocol.load_labware('opentrons_flex_96_filtertiprack_1000ul', 'C4')
    plate1 = protocol.load_labware('opentrons_96_wellplate_200ul_pcr_full_skirt', 'A2') 
    plate2 = protocol.load_labware('corning_96_wellplate_360ul_flat', location='B2') #on heatshaker
    plate3 = protocol.load_labware('opentrons_96_wellplate_200ul_pcr_full_skirt', location='A4')  # New deep well plate for final samples
    reservoir = protocol.load_labware('nest_12_reservoir_15ml', 'C2')
    
    # Liquid definitions
    bsa_standard = protocol.define_liquid(name='BSA Standard', display_color="#FF6F61")      # Bright Coral
    bsa_reag_a = protocol.define_liquid(name='Reagent A', display_color="#FFD700")           # Bright Gold
    bsa_reag_b = protocol.define_liquid(name='Reagent B', display_color="#40E0D0")           # Turquoise
    bsa_reag_c = protocol.define_liquid(name='Reagent C', display_color="#FF69B4")           # Hot Pink
    excess_lysis = protocol.define_liquid(name='Excess Lysis Buffer', display_color="#FFB6C1")  # Light Pink
    copper_sulfate = protocol.define_liquid(name='copper_sulfate', display_color="#8A2BE2")   # Blue Violet
    rhodamine_azide = protocol.define_liquid(name='rhodamine_azide', display_color="#00CED1") # Dark Turquoise
    tcep_click = protocol.define_liquid(name='tcep_click', display_color="#7FFF00")          # Chartreuse
    tbta = protocol.define_liquid(name='tbta', display_color="#FF4500")                      # Orange Red
    loading_buffer = protocol.define_liquid(name='Loading Buffer', display_color="#1E90FF")  # Dodger Blue
    empty = protocol.define_liquid(name='empty', display_color="#FFFFFF")                    # White
    sample_liquids = [protocol.define_liquid(name=f'Sample {i + 1}', display_color="#FFA000") for i in range(protocol.params.num_samples)]  # Amber for samples

    # Reservoir assignments for washes and digestion
    reservoir['A1'].load_liquid(liquid=bsa_reag_a, volume=20000)  
    reservoir['A3'].load_liquid(liquid=bsa_reag_b, volume=20000)  
    reservoir['A5'].load_liquid(liquid=bsa_reag_c, volume=20000)  
    reservoir['A7'].load_liquid(liquid=excess_lysis, volume=15000) 
    reservoir['A9'].load_liquid(liquid=loading_buffer, volume=15000)  
    temp_adapter['A1'].load_liquid(liquid=bsa_standard, volume = 1000)
    temp_adapter['A2'].load_liquid(liquid=copper_sulfate, volume=1000) #click
    temp_adapter['A3'].load_liquid(liquid=rhodamine_azide, volume=100) #click
    temp_adapter['A4'].load_liquid(liquid=tcep_click, volume=1000) #click
    temp_adapter['A5'].load_liquid(liquid=tbta, volume=500) #click
    temp_adapter['A6'].load_liquid(liquid=empty, volume=0) #click

    # Load pipettes
    p50_multi = protocol.load_instrument('flex_8channel_50', 'left') 
    p1000_multi = protocol.load_instrument('flex_8channel_1000', 'right') 

    #Configure the p1000 pipette to use all channels
    p1000_multi.configure_nozzle_layout(style=ALL, tip_racks=[tips_200])

    # Steps 1: Add lysis buffer to column 1 of plate1. 
    p1000_multi.distribute(50, 
         reservoir['A7'],
         plate1[f'A{protocol.params.standards_col}'],
         rate = speed,
         mix_before=(1, 50),
         delay = 2,
         new_tip='once')

    #Step 3: Configure the p50 pipette to use single tip NOTE: this resets the pipettes tip racks! it doesn't
    p50_multi.configure_nozzle_layout(style=SINGLE, start="A1",tip_racks=[partial_50])

    # Step 4: Transfer BSA standard (20 mg/ml) to first well of column 1
    p50_multi.transfer(50,
        temp_adapter['A1'],
        plate1[f'A{protocol.params.standards_col}'],
        rate = 0.35,
        delay = 2,
        mix_after=(3, 40),
        new_tip='once')

    # Step 5: Perform serial dilution down column 1
    rows = ['A','B', 'C', 'D', 'E', 'F', 'G']
    p50_multi.pick_up_tip()
    for source, dest in zip(rows[:-1], rows[1:]):
        p50_multi.transfer(50,
                         plate1[f'{source}{protocol.params.standards_col}'],
                         plate1[f'{dest}{protocol.params.standards_col}'],
                         rate = 0.5,
                         mix_after=(3, 40),
                         new_tip='never', 
                         disposal_vol=0)

    # Step 6: remove excess standard from well G
    p50_multi.aspirate(50,plate1[f'G{protocol.params.standards_col}'])
    p50_multi.drop_tip()

    # assign sample locations dynamically
    sample_locations = []
    for i in range(protocol.params.num_samples):
        if i < 6:  # B1 to B6
            sample_locations.append(f'B{i + 1}')
        elif i < 12:  # C1 to C6
            sample_locations.append(f'C{i - 5}')
        elif i < 18:  # D1 to D6
            sample_locations.append(f'D{i - 11}')
        else:
            break  # Stop if we exceed the number of available rows/columns

    # Predefined list of letters A-H
    row = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']

    # Create a list of rows that repeats based on protocol.params.num_samples
    rows = [row[i % len(row)] for i in range(protocol.params.num_samples)]

    # Create a dynamic sample map based on the assigned sample locations
    sample_map = list(map(lambda i,j :(i,j), rows, sample_locations))

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
        
        #Transfer the samples onto plate 2
        p50_multi.distribute(5,
                        temp_adapter[tube],
                        [plate2[i].bottom(z=0.3) for i in destination_wells],
                        rate = speed,
                        mix_before=(1, 10),
                        disposal_vol=5)  # Distributing to three consecutive columns

    #Step 9: Load the p50 with full tip rack (don't need to)
    p50_multi.configure_nozzle_layout(style=ALL, tip_racks=[partial_50]) #, 

    #Step 10: Pipette triplicate of controls from plate1 column 1 to plate2 columns 1,2,3 
    p50_multi.distribute(5, 
                        plate1[f'A{protocol.params.standards_col}'], 
                        [plate2[f'A{i}'].bottom(z=0.1) for i in range(1, 4)],
                        rate= speed,
                        mix_before=(1, 10),
                        disposal_vol=5)

    
    protocol.move_labware(labware=tips_1000, new_location='C3', use_gripper=True)
    #Step 12: Load the p1000 with full tip rack (don't need to)
    p1000_multi.configure_nozzle_layout(style=ALL, tip_racks=[tips_1000]) #,

    # Step 13: Add reagent A
    p1000_multi.distribute(50,
                        reservoir['A1'],
                        plate2.wells(),
                        new_tip='once',
                        disposal_vol=50)

    # Step 14: Add reagent B
    p1000_multi.distribute(48,
                        reservoir['A3'],
                        plate2.wells(),
                        new_tip='once',
                        disposal_vol=50)

    # Step 15: Add reagent c
    p50_multi.distribute(2,
                        reservoir['A5'],
                        plate2.wells(),
                        new_tip='once',
                        rate = speed,
                        mix_after=(2, 10),
                        disposal_vol=5)

    #Step 16: move plate 2 to the heater shaker and incubate at 37c
    protocol.move_labware(labware=plate2, new_location=heater_shaker, use_gripper=True)
    heater_shaker.set_and_wait_for_temperature(50)
    heater_shaker.close_labware_latch()
    heater_shaker.set_and_wait_for_shake_speed(500)
    protocol.delay(minutes=5)

    #Step 17 deactivate heater shaker and temp modules
    heater_shaker.deactivate_shaker()
    heater_shaker.deactivate_heater()
    heater_shaker.open_labware_latch()

    # ---------------- Normalizing BCA Assay ----------------
    # Tell the user to load BCA assay data
    protocol.comment("Place BCA assay absorbance data in /var/lib/jupyter/notebooks/Data")

    # Pause the protocol until the user loads the file to /var/lib/jupyter/notebooks
    protocol.pause()

    # Tell the robot that new labware will be placed onto the deck
    protocol.move_labware(labware=plate1, new_location='D4', use_gripper=True)
    protocol.move_labware(labware=plate2, new_location='A2', use_gripper=True)
    protocol.move_labware(labware=plate3, new_location="B2", use_gripper=True)
    protocol.move_labware(labware=partial_50, new_location='B4', use_gripper=True)

    #Configure the p1000 pipette to use single tip NOTE: this resets the pipettes tip racks!
    p1000_multi.configure_nozzle_layout(style=SINGLE, start="A1",tip_racks=[tips_200])

    # Define the directory path
    directory = Path("/var/lib/jupyter/notebooks/Data/")

    # Get today's date in YYMMDD format
    today_date = datetime.date.today().strftime("%y%m%d")

    find_file = subprocess.Popen(['python3',"/var/lib/jupyter/notebooks/wait_for_file.py"],stdout=subprocess.PIPE,
        text=True)
    stdout, stderr = find_file.communicate()

    if stderr:
        raise ValueError(f"Error while waiting for file: {stderr}")

    # Extract the file path from the output
    file_path = stdout.splitlines()[1]
    if not file_path:
        raise ValueError("No file path returned by wait_for_file.py")

    protocol.comment(f"Successfully loaded: {file_path}")
    # Read the data file
    df = pd.read_excel(file_path, header=5, nrows=8, usecols="C:N")

    # Create a list of well names (A1 to H12)
    well_names = [f"{row}{col}" for col in range(1, 13) for row in "ABCDEFGH"]

    # Flatten the absorbance values into a single list
    absorbance_values = df.values.flatten()

    # Create the DataFrame
    initial_df = pd.DataFrame({'Well': well_names, 'Absorbance': absorbance_values})

    # Process data for normalization
    samples, replicate_1, replicate_2, replicate_3 = [], [], [], []
    sample_index = 1
    for col_offset in range(0, 12, 3):  # Iterate by column groups (triplets)
        for row_offset in range(8):  # Iterate row-wise for each sample
            start = row_offset * 12 + col_offset  # Starting index for the sample
            if start + 2 < len(initial_df):
                samples.append(f"Sample {sample_index}")
                replicate_1.append(initial_df.iloc[start]['Absorbance'])
                replicate_2.append(initial_df.iloc[start + 1]['Absorbance'])
                replicate_3.append(initial_df.iloc[start + 2]['Absorbance'])
                sample_index += 1

    final_df = pd.DataFrame({
        'Sample': samples,
        'Replicate 1': replicate_1,
        'Replicate 2': replicate_2,
        'Replicate 3': replicate_3
    })

    samples_1_to_8 = final_df.iloc[:8]
    samples_1_to_8['Mean Absorbance'] = samples_1_to_8[['Replicate 1', 'Replicate 2', 'Replicate 3']].mean(axis=1)
    protein_concentrations = [10, 5, 2.5, 1.25, 0.625, 0.3125, 0.15625, 0]
    samples_1_to_8['Protein Concentration (mg/mL)'] = protein_concentrations

    slope, intercept = np.polyfit(samples_1_to_8['Protein Concentration (mg/mL)'], samples_1_to_8['Mean Absorbance'], 1)
    y_pred = slope * samples_1_to_8['Protein Concentration (mg/mL)'] + intercept
    ss_res = np.sum((samples_1_to_8['Mean Absorbance'] - y_pred) ** 2)
    ss_tot = np.sum((samples_1_to_8['Mean Absorbance'] - np.mean(samples_1_to_8['Mean Absorbance'])) ** 2)
    r_squared = 1 - (ss_res / ss_tot)

    unknown_samples = final_df.iloc[8:8 + protocol.params.num_samples]
    unknown_samples['Mean Absorbance'] = unknown_samples[['Replicate 1', 'Replicate 2', 'Replicate 3']].mean(axis=1)
    unknown_samples['Protein Concentration (mg/mL)'] = (unknown_samples['Mean Absorbance'] - intercept) / slope
    unknown_samples['Sample Volume (µL)'] = (protocol.params.target_concentration * protocol.params.final_volume) / unknown_samples['Protein Concentration (mg/mL)']
    unknown_samples['Diluent Volume (µL)'] = protocol.params.final_volume - unknown_samples['Sample Volume (µL)']
    unknown_samples.loc[unknown_samples['Sample Volume (µL)'] > protocol.params.final_volume, ['Sample Volume (µL)', 'Diluent Volume (µL)']] = [protocol.params.final_volume, 0]
    protocol.comment(f"\nNormalized Unknown Samples (to {protocol.params.target_concentration} mg/mL in {protocol.params.final_volume} µL):")
    summary = unknown_samples[['Sample', 'Protein Concentration (mg/mL)', 'Sample Volume (µL)', 'Diluent Volume (µL)']].to_string(index=False)
    protocol.comment(f"\nNormalized sample volumes:\n{summary}")

    normalized_samples = unknown_samples[['Sample', 'Protein Concentration (mg/mL)', 'Sample Volume (µL)', 'Diluent Volume (µL)']].reset_index().drop(columns='index')
    # Write the output and image of data plot to the instrument jupyter notebook directory
    filename = f"Protocol_output_{today_date}.csv"
    output_file_destination_path = directory.joinpath(filename)
    normalized_samples.to_csv(output_file_destination_path)
    rows = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']
    destination_wells  = [f'{rows[i % 8]}{(i // 8)+ 1}' for i in range(len(normalized_samples))]

    for i, row in normalized_samples.iterrows():
        source_well = sample_locations[i]
        normalized_volume = row['Sample Volume (µL)']
        diluent_volume = protocol.params.final_volume - normalized_volume
        destination_well = destination_wells[i]
        p1000_multi.transfer(normalized_volume, temp_adapter[source_well], plate3[destination_well], rate=0.5, new_tip='once')
        p1000_multi.transfer(diluent_volume, reservoir['A7'], plate3[destination_well], rate=0.5, new_tip='once')

    # ---------------- Click Reaction ----------------
    protocol.comment("Running click reaction")
    protocol.move_labware(labware=partial_50, new_location='B3', use_gripper=True)
    protocol.move_labware(labware=tips_1000, new_location='C4', use_gripper=True)
    p50_multi.configure_nozzle_layout(style=SINGLE, start="A1", tip_racks=[partial_50]) #,
    
    #Pipette rhodamine azide (A3), tbta (A5), cuso4 (A2), and tcep (A4)
    p50_multi.transfer(1*(protocol.params.num_samples*2), 
                            temp_adapter['A3'], 
                            temp_adapter['A6'].bottom(z=0.1),
                            rate=speed,
                            mix_before=(1,10), 
                            #delay=2,
                            disposal_vol=1,
                            #blow_out=True,
                            new_tip='always')

    p50_multi.transfer(3*(protocol.params.num_samples*2), 
                            temp_adapter['A5'], 
                            temp_adapter['A6'],
                            mix_before=(1,10),
                            rate=speed,
                            #delay=3, 
                            new_tip='always')

    p50_multi.transfer(1*(protocol.params.num_samples*2), 
                            temp_adapter['A2'], 
                            temp_adapter['A6'], 
                            mix_before=(1,10),
                            new_tip='always')

    p50_multi.transfer(1*(protocol.params.num_samples*2), 
                            temp_adapter['A4'], 
                            temp_adapter['A6'], 
                            #mix_after=(3,30),
                            new_tip='always')
    
    # Make sure the click reagents are well mixed
    click_volume = 6*(protocol.params.final_volume/50)
    # Track where tip racks are currently located
    tiprack_locations = {
        "partial_50": "B3",  # assume starts here
        "tips_1000": "C4",   # assume starts here
    }

    def mix_click_reagents():
        volume_click_reaction = protocol.params.final_volume + click_volume
        location = temp_adapter['A6']
        pipette = None

        positions_mixing = [1, 1, 1]  # default fallback

        if volume_click_reaction < 100:
            positions_mixing = [1, 2, 3]
            pipette = p50_multi

        elif 100 < volume_click_reaction < 200:
            positions_mixing = [1, 4, 9]
            if tiprack_locations["partial_50"] != "B4":
                protocol.move_labware(partial_50, new_location="B4", use_gripper=True)
                tiprack_locations["partial_50"] = "B4"
            p1000_multi.configure_nozzle_layout(style=SINGLE, start="A1", tip_racks=[tips_200])
            pipette = p1000_multi

        elif 200 < volume_click_reaction < 500:
            positions_mixing = [1, 6, 11]
            if tiprack_locations["partial_50"] != "B4":
                protocol.move_labware(partial_50, new_location="B4", use_gripper=True)
                tiprack_locations["partial_50"] = "B4"
            if tiprack_locations["tips_1000"] != "B3":
                protocol.move_labware(tips_1000, new_location="B3", use_gripper=True)
                tiprack_locations["tips_1000"] = "B3"
            p1000_multi.configure_nozzle_layout(style=SINGLE, start="A1", tip_racks=[tips_1000])
            pipette = p1000_multi

        elif 500 < volume_click_reaction < 1000:
            positions_mixing = [1, 10, 16]
            if tiprack_locations["partial_50"] != "B4":
                protocol.move_labware(partial_50, new_location="B4", use_gripper=True)
                tiprack_locations["partial_50"] = "B4"
            if tiprack_locations["tips_1000"] != "B3":
                protocol.move_labware(tips_1000, new_location="B3", use_gripper=True)
                tiprack_locations["tips_1000"] = "B3"
            p1000_multi.configure_nozzle_layout(style=SINGLE, start="A1", tip_racks=[tips_1000])
            pipette = p1000_multi

        else:
            pipette = p1000_multi

        # Perform mixing
        pipette.pick_up_tip()
        pipette.aspirate(protocol.params.final_volume / 2, location.bottom(z=positions_mixing[0]))
        pipette.dispense(protocol.params.final_volume / 2, location.bottom(z=positions_mixing[1]))
        pipette.aspirate(protocol.params.final_volume / 3, location.bottom(z=positions_mixing[2]))
        pipette.dispense(protocol.params.final_volume / 3, location.bottom(z=positions_mixing[0]))
        pipette.mix(3, protocol.params.final_volume, location.bottom(z=positions_mixing[0]))
        pipette.drop_tip()

        # Move tip racks back to original locations in correct order
        if tiprack_locations["tips_1000"] != "C4":
            protocol.move_labware(tips_1000, new_location="C4", use_gripper=True)
            tiprack_locations["tips_1000"] = "C4"
        if tiprack_locations["partial_50"] != "B3":
            protocol.move_labware(partial_50, new_location="B3", use_gripper=True)
            tiprack_locations["partial_50"] = "B3"

    # Call the function
    mix_click_reagents()

    # Pipette the click reaction premix
    p50_multi.transfer(click_volume, 
                            temp_adapter['A6'], 
                            [plate3[i] for i in destination_wells],
                            rate=speed-0.1,
                            delay=2,
                            disposal_vol=0,
                            mix_before=(1, 6),
                            mix_after=(3,30),
                            new_tip='always')

    # Step 11: shake the sample plate for click reaction
    protocol.move_labware(labware=plate3, new_location=heater_shaker, use_gripper=True)
    heater_shaker.close_labware_latch()
    heater_shaker.set_and_wait_for_shake_speed(1000)
    protocol.delay(minutes=90)
    heater_shaker.deactivate_shaker()
    heater_shaker.open_labware_latch()
    thermocycler.open_lid()
    protocol.move_labware(labware=plate3, new_location=thermocycler, use_gripper=True)

    # Add the loading buffer and move to the thermocylcer to seal and store.
    loading_buffer_volume = round((protocol.params.final_volume) / 3, 1)
    columns = sorted(set(well[1:] for well in destination_wells), key=int)
    column_targets = [f'A{col}' for col in columns]
    p50_multi.configure_nozzle_layout(style=ALL, tip_racks=[partial_50])
    p50_multi.transfer(loading_buffer_volume, 
                            reservoir['A9'], 
                            [plate3[well] for well in column_targets],
                            disposal_vol=0,
                            rate=speed-0.1,
                            delay=2,
                            mix_before=(1,30), 
                            mix_after=(3, 40), 
                            new_tip='always')
    thermocycler.close_lid()
    thermocycler.set_block_temperature(95)
    protocol.delay(minutes=5)
    thermocycler.set_block_temperature(4)  # Hold at 4°C