import time
import threading
import os
import sys
from flask import Flask, jsonify
from flask_cors import CORS
import pystray
from PIL import Image

app = Flask(__name__)
CORS(app)

SETTLE_TIME = 5.0
STABILITY_THRESHOLD = 2.0  # Seconds the memory must be static before arming

# Global variables
remote_toggle_latch = False
remote_reset_latch = False
stable_start_time = None
disconnect_start_time = None
memory_stable_since = None
last_seen_parts = []

# Previous tick values
prev_f160_byte1 = 0
prev_f160_byte2 = 0
prev_f161_byte1 = 0

if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATA_FILE = os.path.join(BASE_DIR, "data.txt")

game_data = {
    "AeroPrism": False, "Alshline": False, "EclipseTorch": False, "Elsydeon": False,
    "Hydrofoil": False, "Icedigger": False, "Psychowand": False, "Sapphire": False,
    "platekey": False, "vahalkey": False, "machinekey": False, "Frademantl": False,
    "Algo Ring": False, "Mota Ring": False, "Dezo Ring": False, "Palm Ring": False, "Rykr Ring": False,
    "ambereye": False, "ambereye_count": 0,
    "Aiedo_Cleared": False, "Passageway_Cleared": False, "Kadary_Cleared": False,
    "ZiosFort_Cleared": False, "Nurvus_Cleared": False, "Mile_Cleared": False,
    "TheEdge_Cleared": False, "Piata_Cleared": False, "BirthValley_Cleared": False,
    "BioPlant_Cleared": False, "Wreckage_Cleared": False, "VahalFort_Cleared": False,
    "Molcum_Cleared": False, "ValleyMaze_Cleared": False, "Tonoe_Cleared": False,
    "SoldiersIsland_Cleared": False, "Monsen_Cleared": False, "PlateSystem_Cleared": False,
    "LadeaTower_Cleared": False, "RappyCave_Cleared": False, "Zelan_Cleared": False,
    "Hanger_Cleared": False, "MystVale_Cleared": False, "ClimateControl_Cleared": False,
    "Reshel_Cleared": False, "GaruberkTower_Cleared": False, "EsperMansion_Cleared": False,
    "GumbiousTemple_Cleared": False, "WeaponPlant_Cleared": False, "Strength_Cleared": False,
    "Silence_Cleared": False, "TowerofCourage_Cleared": False, "TowerofAnger_Cleared": False,
    "Kuran_Cleared": False, "AirCastle_Cleared": False,
    "Nalya_Entered": False, "Krup_Entered": False, "Termi_Entered": False,
    "Torinco_Entered": False, "Uzo_Entered": False, "Raja_Entered": False,
    "Ryuon_Entered": False, "Zosa_Entered": False, "Meese_Entered": False,
    "Jut_Entered": False, "AirCastleBasement_Cleared": False
}

def perform_reset():
    global game_data, stable_start_time, disconnect_start_time, memory_stable_since
    stable_start_time = None
    disconnect_start_time = None
    memory_stable_since = None
    
    for key in game_data:
        if isinstance(game_data[key], bool): game_data[key] = False
        elif isinstance(game_data[key], int): game_data[key] = 0
    print("\n[ RESET ] Sniffer wiped. Waiting for stability...")

@app.route('/data', methods=['GET'])
def get_data():
    global remote_toggle_latch, remote_reset_latch
    if stable_start_time and (time.time() - stable_start_time) > SETTLE_TIME:
        # Inject the hotkey states dynamically into the payload response
        response_data = game_data.copy()
        response_data["Remote_Toggle"] = remote_toggle_latch
        response_data["Remote_Reset"] = remote_reset_latch
        
        # Reset the latches immediately so the signal acts as a single "button click"
        remote_toggle_latch = False
        remote_reset_latch = False
        return jsonify(response_data)
    return jsonify({})

@app.route('/remote-toggle', methods=['GET', 'POST'])
def remote_toggle():
    global remote_toggle_latch
    remote_toggle_latch = True
    print("\n[ HOTKEY ] Global Timer Start/Stop received.")
    return jsonify({"status": "success"}), 200

@app.route('/remote-reset', methods=['GET', 'POST'])
def remote_reset():
    global remote_reset_latch
    remote_reset_latch = True
    print("\n[ HOTKEY ] Global Timer Reset received.")
    return jsonify({"status": "success"}), 200

def watch_file():
    global game_data, stable_start_time, disconnect_start_time
    global memory_stable_since, last_seen_parts
    
    print(f"Monitoring {DATA_FILE}...")

    while True:
        try:
            if os.path.exists(DATA_FILE):
                mtime = os.path.getmtime(DATA_FILE)
                with open(DATA_FILE, "r") as f:
                    content = f.read().strip()

                is_live = content != "" and content != "0" and (time.time() - mtime) < 5.0

                if is_live:
                    disconnect_start_time = None
                    if stable_start_time is None:
                        stable_start_time = time.time()
                    
                    try:
                        parts = [int(x) for x in content.split(",")]
                    except:
                        time.sleep(0.2)
                        continue

                    # --- STABILITY GUARD ---
                    # If memory is changing (scrambling), reset the stability timer
                    if parts != last_seen_parts:
                        memory_stable_since = time.time()
                        last_seen_parts = parts
                    
                    stable_duration = time.time() - memory_stable_since if memory_stable_since else 0

                    if len(parts) >= 134:
                        f160_byte1 = parts[97]
                        f160_byte2 = parts[98]
                        f161_byte1 = parts[99]
                        items = parts[134:]

                        # Only process Town/Raja flags if memory has been stable for X seconds
                        # This ignores the random flicker during seed generation
                        if stable_duration > STABILITY_THRESHOLD:

                            # Standard Town Entries (Level Triggered)
                            game_data["Nalya_Entered"]   |= (f160_byte1 & 0x02) != 0
                            game_data["Krup_Entered"]    |= (f160_byte1 & 0x08) != 0
                            game_data["Termi_Entered"]   |= (f160_byte2 & 0x20) != 0
                            game_data["Torinco_Entered"] |= (f160_byte2 & 0x08) != 0
                            game_data["Uzo_Entered"]     |= (f160_byte2 & 0x10) != 0
                            game_data["Ryuon_Entered"]   |= (f161_byte1 & 0x40) != 0
                            game_data["Zosa_Entered"]    |= (f161_byte1 & 0x10) != 0
                            game_data["Meese_Entered"]   |= (f161_byte1 & 0x04) != 0
                            game_data["Jut_Entered"]     |= (f161_byte1 & 0x01) != 0

                            if (f161_byte1 & 0x80) != 0:
                                game_data["Raja_Entered"] = True

                            # --- EVENT FLAGS ---
                            game_data["Wreckage_Cleared"]          = (parts[9]  & 0x80) != 0
                            game_data["Wreckage_Chest_2D"]         = (parts[107] & 0x04) != 0  
                            game_data["Wreckage_Chest_2E"]         = (parts[107] & 0x02) != 0  
                            game_data["Wreckage_Chest_2F"]         = (parts[107] & 0x01) != 0  
                            game_data["Wreckage_Chest_30"]         = (parts[108] & 0x80) != 0  
                            game_data["Wreckage_Chest_31"]         = (parts[108] & 0x40) != 0  

                            game_data["ZiosFort_Cleared"]          = (parts[9]  & 0x20) != 0
                            game_data["ZioFort_Chest_39"]          = (parts[109] & 0x40) != 0  
                            game_data["ZioFort_Chest_3A"]          = (parts[109] & 0x20) != 0  
                            game_data["ZioFort_Chest_3B"]          = (parts[109] & 0x10) != 0  
                            game_data["ZioFort_Chest_3C"]          = (parts[109] & 0x08) != 0  
                            game_data["ZioFort_Chest_3D"]          = (parts[109] & 0x04) != 0  
                            game_data["ZioFort_Chest_3E"]          = (parts[109] & 0x02) != 0  

                            game_data["Mile_Cleared"]              = (parts[4]  & 0x08) != 0
                            game_data["Piata_Cleared"]             = (parts[2]  & 0x01) != 0
                            game_data["Piata_Chest_18"]            = (parts[105] & 0x80) != 0  
                            game_data["Piata_Chest_19"]            = (parts[105] & 0x40) != 0  
                            game_data["Piata_Chest_1A"]            = (parts[105] & 0x20) != 0 

                            game_data["Molcum_Cleared"]            = (parts[3]  & 0x40) != 0
                            game_data["Monsen_Cleared"]            = (parts[8]  & 0x02) != 0
                            game_data["RappyCave_Cleared"]         = (parts[22] & 0x01) != 0
                            game_data["Zelan_Cleared"]             = (parts[15] & 0x80) != 0
                            game_data["Zelan_Chest_0B"]            = (parts[103] & 0x10) != 0
                            game_data["Zelan_Chest_53"]            = (parts[112] & 0x10) != 0  
                            game_data["Zelan_Chest_54"]            = (parts[112] & 0x08) != 0  
                            game_data["Zelan_Chest_55"]            = (parts[112] & 0x04) != 0  
                            game_data["Zelan_Chest_56"]            = (parts[112] & 0x02) != 0  
                            game_data["Zelan_Chest_57"]            = (parts[112] & 0x01) != 0  

                            game_data["MystVale_Cleared"]          = (parts[19] & 0x40) != 0
                            game_data["MystVale_Chest_63"]         = (parts[114] & 0x10) != 0  
                            game_data["MystVale_Chest_64"]         = (parts[114] & 0x08) != 0  

                            game_data["ClimateControl_Cleared"]    = (parts[21] & 0x04) != 0
                            game_data["ClimateControl_Chest_65"]   = (parts[114] & 0x04) != 0  
                            game_data["ClimateControl_Chest_66"]   = (parts[114] & 0x02) != 0  
                            game_data["ClimateControl_Chest_67"]   = (parts[114] & 0x01) != 0  
                            game_data["ClimateControl_Chest_68"]   = (parts[115] & 0x80) != 0  
                            game_data["ClimateControl_Chest_69"]   = (parts[115] & 0x40) != 0  
                            game_data["ClimateControl_Chest_6A"]   = (parts[115] & 0x20) != 0 

                            game_data["Reshel_Cleared"]            = (parts[18] & 0x10) != 0
                            game_data["GaruberkTower_Cleared"]     = (parts[21] & 0x40) != 0
                            game_data["GaruberkTower_Chest_10"]    = (parts[104] & 0x80) != 0  
                            game_data["GaruberkTower_Chest_11"]    = (parts[104] & 0x40) != 0  
                            game_data["GaruberkTower_Chest_12"]    = (parts[104] & 0x20) != 0  
                            game_data["GaruberkTower_Chest_13"]    = (parts[104] & 0x10) != 0  
                            game_data["GaruberkTower_Chest_14"]    = (parts[104] & 0x08) != 0  
                            game_data["GaruberkTower_Chest_15"]    = (parts[104] & 0x04) != 0  
                            game_data["GaruberkTower_Chest_16"]    = (parts[104] & 0x02) != 0  
                            game_data["GaruberkTower_Chest_17"]    = (parts[104] & 0x01) != 0  

                            game_data["EsperMansion_Cleared"]      = (parts[28] & 0x40) != 0
                            game_data["EsperMansion_Chest_6C"]     = (parts[115] & 0x08) != 0  
                            game_data["EsperMansion_Chest_6D"]     = (parts[115] & 0x04) != 0  
                            game_data["EsperMansion_Chest_6E"]     = (parts[115] & 0x02) != 0  
                            game_data["EsperMansion_Chest_6F"]     = (parts[115] & 0x01) != 0

                            game_data["TowerofAnger_Cleared"]      = (parts[29] & 0x40) != 0
                            game_data["TowerOfAnger_Chest_9F"]     = (parts[121] & 0x01) != 0  
                            game_data["TowerOfAnger_Chest_A0"]     = (parts[122] & 0x80) != 0  

                            game_data["PlateSystem_Cleared"]       = (parts[13] & 0x40) != 0
                            game_data["PlateSystem_Chest_3F"]      = (parts[109] & 0x01) != 0  
                            game_data["PlateSystem_Chest_40"]      = (parts[110] & 0x80) != 0  
                            game_data["PlateSystem_Chest_41"]      = (parts[110] & 0x40) != 0  
                            game_data["PlateSystem_Chest_42"]      = (parts[110] & 0x20) != 0  
                            game_data["PlateSystem_Chest_43"]      = (parts[110] & 0x10) != 0  
                            game_data["PlateSystem_Chest_44"]      = (parts[110] & 0x08) != 0  
                            game_data["PlateSystem_Chest_45"]      = (parts[110] & 0x04) != 0  
                            game_data["PlateSystem_Chest_46"]      = (parts[110] & 0x02) != 0  

                            game_data["AirCastle_Cleared"]         = (parts[20] & 0x20) != 0
                            game_data["AirCastle_Chest_79"]        = (parts[117] & 0x40) != 0  
                            game_data["AirCastle_Chest_7A"]        = (parts[117] & 0x20) != 0  
                            game_data["AirCastle_Chest_7B"]        = (parts[117] & 0x10) != 0  
                            game_data["AirCastle_Chest_7C"]        = (parts[117] & 0x08) != 0  
                            game_data["AirCastle_Chest_7D"]        = (parts[117] & 0x04) != 0  
                            game_data["AirCastle_Chest_7E"]        = (parts[117] & 0x02) != 0  
                            game_data["AirCastle_Chest_7F"]        = (parts[117] & 0x01) != 0  
                            game_data["AirCastle_Chest_80"]        = (parts[118] & 0x80) != 0  
                            game_data["AirCastle_Chest_81"]        = (parts[118] & 0x40) != 0  
                            game_data["AirCastle_Chest_82"]        = (parts[118] & 0x20) != 0  

                            game_data["AirCastleBasement_Cleared"] = (parts[21] & 0x02) != 0
                            game_data["AirCastle_Chest_84"]        = (parts[118] & 0x08) != 0  
                            game_data["AirCastle_Chest_85"]        = (parts[118] & 0x04) != 0  
                            game_data["AirCastle_Chest_0C"]        = (parts[103] & 0x08) != 0  

                            game_data["BioPlant_Cleared"]          = (parts[8]  & 0x80) != 0
                            game_data["BioPlant_Chest_26"]         = (parts[106] & 0x02) != 0  
                            game_data["BioPlant_Chest_29"]         = (parts[107] & 0x40) != 0 
                            game_data["BioPlant_Chest_2B"]         = (parts[107] & 0x10) != 0  
                            game_data["BioPlant_Chest_2C"]         = (parts[107] & 0x08) != 0  

                            game_data["VahalFort_Cleared"]         = (parts[23] & 0x02) != 0
                            game_data["VahalFort_Chest_8C"]        = (parts[119] & 0x08) != 0  
                            game_data["VahalFort_Chest_8D"]        = (parts[119] & 0x04) != 0  
                            game_data["VahalFort_Chest_8E"]        = (parts[119] & 0x02) != 0  
                            game_data["VahalFort_Chest_8F"]        = (parts[119] & 0x01) != 0  
                            game_data["VahalFort_Chest_90"]        = (parts[120] & 0x80) != 0 

                            game_data["Hanger_Cleared"]            = (parts[17] & 0x20) != 0
                            game_data["Hangar_Chest_59"]           = (parts[113] & 0x40) != 0 
                            game_data["Hangar_Chest_5A"]           = (parts[113] & 0x20) != 0  

                            game_data["Kuran_Cleared"]             = (parts[18] & 0x40) != 0
                            game_data["Kuran_Chest_5C"]            = (parts[113] & 0x08) != 0  
                            game_data["Kuran_Chest_5E"]            = (parts[113] & 0x02) != 0  
                            game_data["Kuran_Chest_5F"]            = (parts[113] & 0x01) != 0  
                            game_data["Kuran_Chest_60"]            = (parts[114] & 0x80) != 0  
                            game_data["Kuran_Chest_61"]            = (parts[114] & 0x40) != 0  
                            game_data["Kuran_Chest_62"]            = (parts[114] & 0x20) != 0  

                            game_data["Nurvus_Cleared"]            = (parts[14] & 0x80) != 0
                            game_data["Nurvus_Chest_4D"]           = (parts[111] & 0x04) != 0  
                            game_data["Nurvus_Chest_4E"]           = (parts[111] & 0x02) != 0  
                            game_data["Nurvus_Chest_4F"]           = (parts[111] & 0x01) != 0  
                            game_data["Nurvus_Chest_51"]           = (parts[112] & 0x40) != 0  
                            game_data["Nurvus_Chest_52"]           = (parts[112] & 0x20) != 0  

                            # Chests
                            game_data["Aiedo_Cleared"]             = (parts[108] & 0x10) != 0
                            game_data["Aiedo_Chest_32"]            = (parts[108] & 0x20) != 0  

                            game_data["Silence_Cleared"]           = (parts[120] & 0x20) != 0
                            game_data["SilenceTower_Chest_91"]     = (parts[120] & 0x40) != 0  
                            game_data["SilenceTower_Chest_93"]     = (parts[120] & 0x10) != 0  
                            game_data["SilenceTower_Chest_94"]     = (parts[120] & 0x08) != 0  

                            game_data["Passageway_Cleared"]        = (parts[108] & 0x02) != 0
                            game_data["Passageway_Chest_35"]       = (parts[108] & 0x04) != 0 

                            game_data["Kadary_Cleared"]            = (parts[108] & 0x01) != 0
                            game_data["ValleyMaze_Cleared"]        = (parts[105] & 0x02) != 0
                            game_data["ValleyMaze_Chest_1D"]       = (parts[105] & 0x04) != 0 

                            game_data["Tonoe_Cleared"]             = (parts[103] & 0x80) != 0
                            game_data["Tonoe_Chest_1F"]            = (parts[105] & 0x01) != 0  
                            game_data["Tonoe_Chest_20"]            = (parts[106] & 0x80) != 0  
                            game_data["Tonoe_Chest_21"]            = (parts[106] & 0x40) != 0  
                            game_data["Tonoe_Chest_22"]            = (parts[106] & 0x20) != 0  
                            game_data["Tonoe_Chest_23"]            = (parts[106] & 0x10) != 0  
                            game_data["Tonoe_Chest_24"]            = (parts[106] & 0x08) != 0
                            game_data["Tonoe_Chest_A6"]            = (parts[122] & 0x02) != 0    

                            game_data["LadeaTower_Cleared"]        = (parts[103] & 0x40) != 0
                            game_data["LadeaTower_Chest_47"]       = (parts[110] & 0x01) != 0  
                            game_data["LadeaTower_Chest_48"]       = (parts[111] & 0x80) != 0  
                            game_data["LadeaTower_Chest_49"]       = (parts[111] & 0x40) != 0  
                            game_data["LadeaTower_Chest_4A"]       = (parts[111] & 0x20) != 0  
                            game_data["LadeaTower_Chest_4B"]       = (parts[111] & 0x10) != 0  
                            game_data["LadeaTower_Chest_A8"]       = (parts[123] & 0x80) != 0  

                            game_data["GumbiousTemple_Cleared"]    = (parts[116] & 0x10) != 0
                            game_data["GumbiousTemple_Chest_70"]   = (parts[116] & 0x80) != 0  
                            game_data["GumbiousTemple_Chest_71"]   = (parts[116] & 0x40) != 0  
                            game_data["GumbiousTemple_Chest_72"]   = (parts[116] & 0x20) != 0 

                            game_data["WeaponPlant_Cleared"]       = (parts[116] & 0x04) != 0
                            game_data["WeaponPlant_Chest_74"]      = (parts[116] & 0x08) != 0  
                            game_data["WeaponPlant_Chest_76"]      = (parts[116] & 0x02) != 0  
                            game_data["WeaponPlant_Chest_77"]      = (parts[116] & 0x01) != 0 

                            game_data["Strength_Cleared"]          = (parts[122] & 0x10) != 0
                            game_data["TowerOfStrength_Chest_95"]  = (parts[120] & 0x04) != 0  
                            game_data["TowerOfStrength_Chest_96"]  = (parts[120] & 0x02) != 0  
                            game_data["TowerOfStrength_Chest_97"]  = (parts[120] & 0x01) != 0  
                            game_data["TowerOfStrength_Chest_98"]  = (parts[121] & 0x80) != 0  
                            game_data["TowerOfStrength_Chest_99"]  = (parts[121] & 0x40) != 0  
                            game_data["TowerOfStrength_Chest_A1"]  = (parts[122] & 0x40) != 0  
                            game_data["TowerOfStrength_Chest_A2"]  = (parts[122] & 0x20) != 0  

                            game_data["TowerofCourage_Cleared"]    = (parts[122] & 0x04) != 0
                            game_data["TowerOfCourage_Chest_9B"]   = (parts[121] & 0x10) != 0  
                            game_data["TowerOfCourage_Chest_9C"]   = (parts[121] & 0x08) != 0  
                            game_data["TowerOfCourage_Chest_9D"]   = (parts[121] & 0x04) != 0  
                            game_data["TowerOfCourage_Chest_9E"]   = (parts[121] & 0x02) != 0
                            game_data["TowerOfCourage_Chest_A4"]   = (parts[122] & 0x08) != 0  
                            game_data["TowerOfCourage_Chest_A5"]   = (parts[122] & 0x04) != 0    


                            game_data["SoldiersIsland_Cleared"]    = (parts[103] & 0x04) != 0
                            game_data["SoldiersIsland_Chest_86"]   = (parts[118] & 0x02) != 0  
                            game_data["SoldiersIsland_Chest_87"]   = (parts[118] & 0x01) != 0  
                            game_data["SoldiersIsland_Chest_88"]   = (parts[119] & 0x80) != 0  
                            game_data["SoldiersIsland_Chest_89"]   = (parts[119] & 0x40) != 0  
                            game_data["SoldiersIsland_Chest_8A"]   = (parts[119] & 0x20) != 0  

                            game_data["BirthValley_Cleared"]       = (parts[106] & 0x04) != 0
                            game_data["BirthValley_Chest_1B"]      = (parts[105] & 0x10) != 0  
                            game_data["BirthValley_Chest_1C"]      = (parts[105] & 0x08) != 0  

                            if len(items) >= 19:
                                game_data["Hydrofoil"]    = (items[1]  == 1)
                                game_data["Icedigger"]    = (items[2]  == 1)
                                game_data["Elsydeon"]     = (items[3]  == 1)
                                game_data["AeroPrism"]    = (items[4]  == 1)
                                game_data["Alshline"]     = (items[5]  == 1)
                                game_data["EclipseTorch"] = (items[6]  == 1)
                                game_data["Psychowand"]   = (items[7]  == 1)
                                game_data["Sapphire"]     = (items[8]  == 1)
                                game_data["platekey"]     = (items[9]  == 1)
                                game_data["vahalkey"]     = (items[10] == 1)
                                game_data["machinekey"]   = (items[11] == 1)
                                game_data["Frademantl"]   = (items[12] == 1)
                                game_data["Algo Ring"]    = (items[17] == 1)
                                game_data["Mota Ring"]    = (items[14] == 1)
                                game_data["Dezo Ring"]    = (items[15] == 1)
                                game_data["Palm Ring"]    = (items[13] == 1)
                                game_data["Rykr Ring"]    = (items[16] == 1)
                                game_data["ambereye"]       = (items[0] > 0)
                                game_data["ambereye_count"] = items[0]

                        print(f"STABILITY: {stable_duration:.1f}s | Raja: {game_data['Raja_Entered']}    ", end="\r")

                else:
                    if stable_start_time is not None:
                        if disconnect_start_time is None:
                            disconnect_start_time = time.time()
                        if (time.time() - disconnect_start_time) > 5.0:
                            perform_reset()
        except Exception as e:
            print(f"\n[ ERROR ] {e}")
        time.sleep(0.2)

def setup_tray():
    icon_path = os.path.join(BASE_DIR, "tracker.ico")
    try: image = Image.open(icon_path)
    except: image = Image.new('RGB', (64, 64), color=(0, 229, 255))
    def restart(icon, item):
        perform_reset(); icon.stop(); os.execl(sys.executable, sys.executable, *sys.argv)
    menu = (pystray.MenuItem('Restart', restart), pystray.MenuItem('Quit', lambda i, j: os._exit(0)))
    icon = pystray.Icon("PS4_Tracker", image, "PS4 Tracker", menu)
    icon.run()

if __name__ == '__main__':
    threading.Thread(target=watch_file, daemon=True).start()
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=8080), daemon=True).start()
    setup_tray()
