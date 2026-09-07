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
STABILITY_THRESHOLD = 2.0  # Seconds memory must be static before processing flags

# Global state trackers
remote_toggle_latch = False
remote_reset_latch = False
stable_start_time = None
disconnect_start_time = None
memory_stable_since = None
last_seen_parts = []
last_triggered_event = "None"

# Re-entrance Map Pointer Lookups (16-bit hex from 0xFFECFA)
REENTRANCE_MAP_POINTERS = {
    "3EF8": "Nalya_Entered",
    "8624": "Krup_Entered",
    "60C8": "Termi_Entered",
    "1548": "Torinco_Entered",
    "0A60": "Uzo_Entered",
    "793C": "Ryuon_Entered",
    "9A5C": "Raja_Entered",
    "8D9E": "Zosa_Entered",
    "C88E": "Meese_Entered",
    "F6F6": "Jut_Entered"
}

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

def set_flag(key, new_value):
    """Updates game_data and records the name of the last triggered event."""
    global game_data, last_triggered_event
    old_value = game_data.get(key)
    
    if old_value != new_value:
        game_data[key] = new_value
        if new_value:
            last_triggered_event = f"{key}: {new_value}"

def perform_reset():
    global game_data, stable_start_time, disconnect_start_time, memory_stable_since
    stable_start_time = None
    disconnect_start_time = None
    memory_stable_since = None

    for key in game_data:
        if isinstance(game_data[key], bool): 
            game_data[key] = False
        elif isinstance(game_data[key], int): 
            game_data[key] = 0
    print("\n[ RESET ] Sniffer wiped. Waiting for stability...")

@app.route('/data', methods=['GET'])
def get_data():
    global remote_toggle_latch, remote_reset_latch

    response_data = game_data.copy()
    response_data["Remote_Toggle"] = remote_toggle_latch
    response_data["Remote_Reset"] = remote_reset_latch

    remote_toggle_latch = False
    remote_reset_latch = False

    return jsonify(response_data)

@app.route('/toggle', methods=['GET', 'POST'])
@app.route('/remote-toggle', methods=['GET', 'POST'])
def remote_toggle():
    global remote_toggle_latch
    remote_toggle_latch = True
    print("\n[ HOTKEY ] Global Timer Start/Stop received.")
    return jsonify({"status": "success"}), 200

@app.route('/reset', methods=['GET', 'POST'])
@app.route('/remote-reset', methods=['GET', 'POST'])
@app.route('/remote_reset', methods=['GET', 'POST'])
@app.route('/reset_timer', methods=['GET', 'POST'])
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

                    raw_tokens = content.split(",")

                    # Extract map hex string (4 characters, uppercase) appended at end of data.txt
                    map_pointer_hex = raw_tokens[-1].strip().upper() if raw_tokens else ""

                    try:
                        # Convert all integer components prior to the final map hex string
                        parts = [int(x) for x in raw_tokens[:-1]]
                    except ValueError:
                        time.sleep(0.2)
                        continue

                    # Memory stability monitor (prevents flickering during seed setup)
                    if parts != last_seen_parts:
                        memory_stable_since = time.time()
                        last_seen_parts = parts

                    stable_duration = time.time() - memory_stable_since if memory_stable_since else 0

                    if len(parts) >= 134:
                        items = parts[134:]

                        if stable_duration > STABILITY_THRESHOLD:
                            # --- 1. RE-ENTRANCE LOCATION TRACKING (0xECFA Hex Pointer) ---
                            if map_pointer_hex in REENTRANCE_MAP_POINTERS:
                                target_flag = REENTRANCE_MAP_POINTERS[map_pointer_hex]
                                set_flag(target_flag, True)

                            # --- 2. EVENT FLAGS ---
                            set_flag("Wreckage_Cleared", (parts[9] & 0x80) != 0)
                            set_flag("Wreckage_Chest_2D", (parts[107] & 0x04) != 0)  
                            set_flag("Wreckage_Chest_2E", (parts[107] & 0x02) != 0)  
                            set_flag("Wreckage_Chest_2F", (parts[107] & 0x01) != 0)  
                            set_flag("Wreckage_Chest_30", (parts[108] & 0x80) != 0)  
                            set_flag("Wreckage_Chest_31", (parts[108] & 0x40) != 0)  

                            set_flag("ZiosFort_Cleared", (parts[9] & 0x20) != 0)
                            set_flag("ZioFort_Chest_39", (parts[109] & 0x40) != 0)  
                            set_flag("ZioFort_Chest_3A", (parts[109] & 0x20) != 0)  
                            set_flag("ZioFort_Chest_3B", (parts[109] & 0x10) != 0)  
                            set_flag("ZioFort_Chest_3C", (parts[109] & 0x08) != 0)  
                            set_flag("ZioFort_Chest_3D", (parts[109] & 0x04) != 0)  
                            set_flag("ZioFort_Chest_3E", (parts[109] & 0x02) != 0)  

                            set_flag("Mile_Cleared", (parts[4] & 0x08) != 0)
                            set_flag("Piata_Cleared", (parts[2] & 0x01) != 0)
                            set_flag("Piata_Chest_18", (parts[105] & 0x80) != 0)  
                            set_flag("Piata_Chest_19", (parts[105] & 0x40) != 0)  
                            set_flag("Piata_Chest_1A", (parts[105] & 0x20) != 0) 

                            set_flag("Molcum_Cleared", (parts[3] & 0x40) != 0)
                            set_flag("Monsen_Cleared", (parts[8] & 0x02) != 0)
                            set_flag("RappyCave_Cleared", (parts[24] & 0x20) != 0)
                            set_flag("Zelan_Cleared", (parts[15] & 0x80) != 0)
                            set_flag("Zelan_Chest_0B", (parts[103] & 0x10) != 0)
                            set_flag("Zelan_Chest_53", (parts[112] & 0x10) != 0)  
                            set_flag("Zelan_Chest_54", (parts[112] & 0x08) != 0)  
                            set_flag("Zelan_Chest_55", (parts[112] & 0x04) != 0)  
                            set_flag("Zelan_Chest_56", (parts[112] & 0x02) != 0)  
                            set_flag("Zelan_Chest_57", (parts[112] & 0x01) != 0)  

                            set_flag("MystVale_Cleared", (parts[19] & 0x40) != 0)
                            set_flag("MystVale_Chest_63", (parts[114] & 0x10) != 0)  
                            set_flag("MystVale_Chest_64", (parts[114] & 0x08) != 0)  

                            set_flag("ClimateControl_Cleared", (parts[21] & 0x04) != 0)
                            set_flag("ClimateControl_Chest_65", (parts[114] & 0x04) != 0)  
                            set_flag("ClimateControl_Chest_66", (parts[114] & 0x02) != 0)  
                            set_flag("ClimateControl_Chest_67", (parts[114] & 0x01) != 0)  
                            set_flag("ClimateControl_Chest_68", (parts[115] & 0x80) != 0)  
                            set_flag("ClimateControl_Chest_69", (parts[115] & 0x40) != 0)  
                            set_flag("ClimateControl_Chest_6A", (parts[115] & 0x20) != 0) 

                            set_flag("Reshel_Cleared", (parts[18] & 0x10) != 0)
                            set_flag("GaruberkTower_Cleared", (parts[21] & 0x40) != 0)
                            set_flag("GaruberkTower_Chest_10", (parts[104] & 0x80) != 0)  
                            set_flag("GaruberkTower_Chest_11", (parts[104] & 0x40) != 0)  
                            set_flag("GaruberkTower_Chest_12", (parts[104] & 0x20) != 0)  
                            set_flag("GaruberkTower_Chest_13", (parts[104] & 0x10) != 0)  
                            set_flag("GaruberkTower_Chest_14", (parts[104] & 0x08) != 0)  
                            set_flag("GaruberkTower_Chest_15", (parts[104] & 0x04) != 0)  
                            set_flag("GaruberkTower_Chest_16", (parts[104] & 0x02) != 0)  
                            set_flag("GaruberkTower_Chest_17", (parts[104] & 0x01) != 0)  

                            set_flag("EsperMansion_Cleared", (parts[28] & 0x40) != 0)
                            set_flag("EsperMansion_Chest_6C", (parts[115] & 0x08) != 0)  
                            set_flag("EsperMansion_Chest_6D", (parts[115] & 0x04) != 0)  
                            set_flag("EsperMansion_Chest_6E", (parts[115] & 0x02) != 0)  
                            set_flag("EsperMansion_Chest_6F", (parts[115] & 0x01) != 0)

                            set_flag("TowerofAnger_Cleared", (parts[29] & 0x40) != 0)
                            set_flag("TowerOfAnger_Chest_9F", (parts[121] & 0x01) != 0)  
                            set_flag("TowerOfAnger_Chest_A0", (parts[122] & 0x80) != 0)  

                            set_flag("PlateSystem_Cleared", (parts[13] & 0x40) != 0)
                            set_flag("PlateSystem_Chest_3F", (parts[109] & 0x01) != 0)  
                            set_flag("PlateSystem_Chest_40", (parts[110] & 0x80) != 0)  
                            set_flag("PlateSystem_Chest_41", (parts[110] & 0x40) != 0)  
                            set_flag("PlateSystem_Chest_42", (parts[110] & 0x20) != 0)  
                            set_flag("PlateSystem_Chest_43", (parts[110] & 0x10) != 0)  
                            set_flag("PlateSystem_Chest_44", (parts[110] & 0x08) != 0)  
                            set_flag("PlateSystem_Chest_45", (parts[110] & 0x04) != 0)  
                            set_flag("PlateSystem_Chest_46", (parts[110] & 0x02) != 0)  

                            set_flag("AirCastle_Cleared", (parts[20] & 0x20) != 0)
                            set_flag("AirCastle_Chest_79", (parts[117] & 0x40) != 0)  
                            set_flag("AirCastle_Chest_7A", (parts[117] & 0x20) != 0)  
                            set_flag("AirCastle_Chest_7B", (parts[117] & 0x10) != 0)  
                            set_flag("AirCastle_Chest_7C", (parts[117] & 0x08) != 0)  
                            set_flag("AirCastle_Chest_7D", (parts[117] & 0x04) != 0)  
                            set_flag("AirCastle_Chest_7E", (parts[117] & 0x02) != 0)  
                            set_flag("AirCastle_Chest_7F", (parts[117] & 0x01) != 0)  
                            set_flag("AirCastle_Chest_80", (parts[118] & 0x80) != 0)  
                            set_flag("AirCastle_Chest_81", (parts[118] & 0x40) != 0)  
                            set_flag("AirCastle_Chest_82", (parts[118] & 0x20) != 0)  

                            set_flag("AirCastleBasement_Cleared", (parts[21] & 0x02) != 0)
                            set_flag("AirCastle_Chest_84", (parts[118] & 0x08) != 0)  
                            set_flag("AirCastle_Chest_85", (parts[118] & 0x04) != 0)  
                            set_flag("AirCastle_Chest_0C", (parts[103] & 0x08) != 0)  

                            set_flag("BioPlant_Cleared", (parts[8] & 0x80) != 0)
                            set_flag("BioPlant_Chest_26", (parts[106] & 0x02) != 0)  
                            set_flag("BioPlant_Chest_29", (parts[107] & 0x40) != 0) 
                            set_flag("BioPlant_Chest_2B", (parts[107] & 0x10) != 0)  
                            set_flag("BioPlant_Chest_2C", (parts[107] & 0x08) != 0)  

                            set_flag("VahalFort_Cleared", (parts[23] & 0x02) != 0)
                            set_flag("VahalFort_Chest_8C", (parts[119] & 0x08) != 0)  
                            set_flag("VahalFort_Chest_8D", (parts[119] & 0x04) != 0)  
                            set_flag("VahalFort_Chest_8E", (parts[119] & 0x02) != 0)  
                            set_flag("VahalFort_Chest_8F", (parts[119] & 0x01) != 0)  
                            set_flag("VahalFort_Chest_90", (parts[120] & 0x80) != 0) 

                            set_flag("Hanger_Cleared", (parts[17] & 0x20) != 0)
                            set_flag("Hangar_Chest_59", (parts[113] & 0x40) != 0) 
                            set_flag("Hangar_Chest_5A", (parts[113] & 0x20) != 0)  

                            set_flag("Kuran_Cleared", (parts[18] & 0x40) != 0)
                            set_flag("Kuran_Chest_5C", (parts[113] & 0x08) != 0)  
                            set_flag("Kuran_Chest_5E", (parts[113] & 0x02) != 0)  
                            set_flag("Kuran_Chest_5F", (parts[113] & 0x01) != 0)  
                            set_flag("Kuran_Chest_60", (parts[114] & 0x80) != 0)  
                            set_flag("Kuran_Chest_61", (parts[114] & 0x40) != 0)  
                            set_flag("Kuran_Chest_62", (parts[114] & 0x20) != 0)  

                            set_flag("Nurvus_Cleared", (parts[14] & 0x80) != 0)
                            set_flag("Nurvus_Chest_4D", (parts[111] & 0x04) != 0)  
                            set_flag("Nurvus_Chest_4E", (parts[111] & 0x02) != 0)  
                            set_flag("Nurvus_Chest_4F", (parts[111] & 0x01) != 0)  
                            set_flag("Nurvus_Chest_51", (parts[112] & 0x40) != 0)  
                            set_flag("Nurvus_Chest_52", (parts[112] & 0x20) != 0)  

                            set_flag("Aiedo_Cleared", (parts[108] & 0x10) != 0)
                            set_flag("Aiedo_Chest_32", (parts[108] & 0x20) != 0)  

                            set_flag("Silence_Cleared", (parts[120] & 0x20) != 0)
                            set_flag("SilenceTower_Chest_91", (parts[120] & 0x40) != 0)  
                            set_flag("SilenceTower_Chest_93", (parts[120] & 0x10) != 0)  
                            set_flag("SilenceTower_Chest_94", (parts[120] & 0x08) != 0)  

                            set_flag("Passageway_Cleared", (parts[108] & 0x02) != 0)
                            set_flag("Passageway_Chest_35", (parts[108] & 0x04) != 0) 

                            set_flag("Kadary_Cleared", (parts[108] & 0x01) != 0)
                            set_flag("ValleyMaze_Cleared", (parts[105] & 0x02) != 0)
                            set_flag("ValleyMaze_Chest_1D", (parts[105] & 0x04) != 0) 

                            set_flag("Tonoe_Cleared", (parts[103] & 0x80) != 0)
                            set_flag("Tonoe_Chest_1F", (parts[105] & 0x01) != 0)  
                            set_flag("Tonoe_Chest_20", (parts[106] & 0x80) != 0)  
                            set_flag("Tonoe_Chest_21", (parts[106] & 0x40) != 0)  
                            set_flag("Tonoe_Chest_22", (parts[106] & 0x20) != 0)  
                            set_flag("Tonoe_Chest_23", (parts[106] & 0x10) != 0)  
                            set_flag("Tonoe_Chest_24", (parts[106] & 0x08) != 0)
                            set_flag("Tonoe_Chest_A6", (parts[122] & 0x02) != 0)    

                            set_flag("LadeaTower_Cleared", (parts[103] & 0x40) != 0)
                            set_flag("LadeaTower_Chest_47", (parts[110] & 0x01) != 0)  
                            set_flag("LadeaTower_Chest_48", (parts[111] & 0x80) != 0)  
                            set_flag("LadeaTower_Chest_49", (parts[111] & 0x40) != 0)  
                            set_flag("LadeaTower_Chest_4A", (parts[111] & 0x20) != 0)  
                            set_flag("LadeaTower_Chest_4B", (parts[111] & 0x10) != 0)  
                            set_flag("LadeaTower_Chest_A8", (parts[123] & 0x80) != 0)  

                            set_flag("GumbiousTemple_Cleared", (parts[116] & 0x10) != 0)
                            set_flag("GumbiousTemple_Chest_70", (parts[116] & 0x80) != 0)  
                            set_flag("GumbiousTemple_Chest_71", (parts[116] & 0x40) != 0)  
                            set_flag("GumbiousTemple_Chest_72", (parts[116] & 0x20) != 0) 

                            set_flag("WeaponPlant_Cleared", (parts[116] & 0x04) != 0)
                            set_flag("WeaponPlant_Chest_74", (parts[116] & 0x08) != 0)  
                            set_flag("WeaponPlant_Chest_76", (parts[116] & 0x02) != 0)  
                            set_flag("WeaponPlant_Chest_77", (parts[116] & 0x01) != 0) 

                            set_flag("Strength_Cleared", (parts[122] & 0x10) != 0)
                            set_flag("TowerOfStrength_Chest_95", (parts[120] & 0x04) != 0)  
                            set_flag("TowerOfStrength_Chest_96", (parts[120] & 0x02) != 0)  
                            set_flag("TowerOfStrength_Chest_97", (parts[120] & 0x01) != 0)  
                            set_flag("TowerOfStrength_Chest_98", (parts[121] & 0x80) != 0)  
                            set_flag("TowerOfStrength_Chest_99", (parts[121] & 0x40) != 0)  
                            set_flag("TowerOfStrength_Chest_A1", (parts[122] & 0x40) != 0)  
                            set_flag("TowerOfStrength_Chest_A2", (parts[122] & 0x20) != 0)  

                            set_flag("TowerofCourage_Cleared", (parts[122] & 0x04) != 0)
                            set_flag("TowerOfCourage_Chest_9B", (parts[121] & 0x10) != 0)  
                            set_flag("TowerOfCourage_Chest_9C", (parts[121] & 0x08) != 0)  
                            set_flag("TowerOfCourage_Chest_9D", (parts[121] & 0x04) != 0)  
                            set_flag("TowerOfCourage_Chest_9E", (parts[121] & 0x02) != 0)
                            set_flag("TowerOfCourage_Chest_A4", (parts[122] & 0x08) != 0)     

                            set_flag("SoldiersIsland_Cleared", (parts[103] & 0x04) != 0)
                            set_flag("SoldiersIsland_Chest_86", (parts[118] & 0x02) != 0)  
                            set_flag("SoldiersIsland_Chest_87", (parts[118] & 0x01) != 0)  
                            set_flag("SoldiersIsland_Chest_88", (parts[119] & 0x80) != 0)  
                            set_flag("SoldiersIsland_Chest_89", (parts[119] & 0x40) != 0)  
                            set_flag("SoldiersIsland_Chest_8A", (parts[119] & 0x20) != 0)  

                            set_flag("BirthValley_Cleared", (parts[106] & 0x04) != 0)
                            set_flag("BirthValley_Chest_1B", (parts[105] & 0x10) != 0)  
                            set_flag("BirthValley_Chest_1C", (parts[105] & 0x08) != 0)  

                            # --- 3. ITEMS ---
                            if len(items) >= 19:
                                set_flag("Hydrofoil", items[1] == 1)
                                set_flag("Icedigger", items[2] == 1)
                                set_flag("Elsydeon", items[3] == 1)
                                set_flag("AeroPrism", items[4] == 1)
                                set_flag("Alshline", items[5] == 1)
                                set_flag("EclipseTorch", items[6] == 1)
                                set_flag("Psychowand", items[7] == 1)
                                set_flag("Sapphire", items[8] == 1)
                                set_flag("platekey", items[9] == 1)
                                set_flag("vahalkey", items[10] == 1)
                                set_flag("machinekey", items[11] == 1)
                                set_flag("Frademantl", items[12] == 1)
                                set_flag("Algo Ring", items[17] == 1)
                                set_flag("Mota Ring", items[14] == 1)
                                set_flag("Dezo Ring", items[15] == 1)
                                set_flag("Palm Ring", items[13] == 1)
                                set_flag("Rykr Ring", items[16] == 1)
                                set_flag("ambereye", items[0] > 0)
                                set_flag("ambereye_count", items[0])

                        print(f"STABILITY: {stable_duration:.1f}s | Last Trigger: {last_triggered_event:<35}", end="\r")

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
    try: 
        image = Image.open(icon_path)
    except Exception: 
        image = Image.new('RGB', (64, 64), color=(0, 229, 255))
        
    def restart(icon, item):
        perform_reset()
        icon.stop()
        os.execl(sys.executable, sys.executable, *sys.argv)
        
    menu = (
        pystray.MenuItem('Restart', restart), 
        pystray.MenuItem('Quit', lambda i, j: os._exit(0))
    )
    icon = pystray.Icon("PS4_Tracker", image, "PS4 Tracker", menu)
    icon.run()

if __name__ == '__main__':
    threading.Thread(target=watch_file, daemon=True).start()
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=8080), daemon=True).start()
    setup_tray()
