#!/usr/bin/env python3
"""
Last Horizon: Core Protocol - Level Generator via UEFN MCP
Automates the placement, transformation, parameter configuration,
and event wiring of all devices and gameplay zones for the level.
"""

import urllib.request
import json
import time
import sys

URL = 'http://127.0.0.1:8000/mcp'

class UefnMcpClient:
    def __init__(self, url=URL):
        self.url = url
        self.session_id = None
        self.init()

    def rpc(self, method, params):
        payload = {
            'jsonrpc': '2.0',
            'id': 1,
            'method': method,
            'params': params
        }
        headers = {'Content-Type': 'application/json'}
        if self.session_id:
            headers['Mcp-Session-Id'] = self.session_id
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(self.url, data=data, headers=headers)
        with urllib.request.urlopen(req) as resp:
            resp_session = resp.headers.get('Mcp-Session-Id')
            if resp_session:
                self.session_id = resp_session
            body = resp.read().decode('utf-8')
            return json.loads(body)

    def init(self):
        print(f"[*] Initializing connection to UEFN MCP ({self.url})...")
        res = self.rpc('initialize', {
            'protocolVersion': '2024-11-05',
            'capabilities': {},
            'clientInfo': {'name': 'LastHorizonBuilder', 'version': '1.0'}
        })
        print(f"[+] Connected! Session: {self.session_id}")

    def call_tool(self, toolset, tool, args):
        payload = {
            'toolset_name': toolset,
            'tool_name': tool,
            'arguments': args
        }
        res = self.rpc('tools/call', {'name': 'call_tool', 'arguments': payload})
        if res.get('result', {}).get('isError'):
            err = res['result']['content'][0]['text']
            raise RuntimeError(f"Tool error ({tool}): {err}")
        content = res.get('result', {}).get('content', [])
        if content and content[0].get('type') == 'text':
            try:
                return json.loads(content[0]['text'])
            except:
                return content[0]['text']
        return res

    def build_verse(self):
        print("[*] Compiling Verse scripts inside UEFN...")
        res = self.call_tool('ValkyrieToolset.VerseToolset', 'BuildAll', {})
        print(f"[+] Verse compilation completed: {res}")
        return res

    def place_device(self, asset_ref, x, y, z=1155.0, yaw=0.0, pitch=0.0, roll=0.0, scale_x=1.0, scale_y=1.0, scale_z=1.0):
        res = self.call_tool('ValkyrieToolset.DeviceToolset', 'PlaceDevice', {
            'assetPath': {'refPath': asset_ref},
            'transform': {
                'location': {'x': float(x), 'y': float(y), 'z': float(z)},
                'rotation': {'pitch': float(pitch), 'yaw': float(yaw), 'roll': float(roll)},
                'scale': {'x': float(scale_x), 'y': float(scale_y), 'z': float(scale_z)}
            }
        })
        ref = res.get('returnValue', {}).get('refPath')
        return ref

    def set_device_property(self, device_ref, prop_name, value):
        if isinstance(value, (dict, list)):
            val_str = json.dumps(value)
        elif isinstance(value, str) and not (value.startswith('{') or value.startswith('[')):
            val_str = json.dumps(value)
        else:
            val_str = str(value)

        return self.call_tool('ValkyrieToolset.DeviceToolset', 'SetDeviceProperty', {
            'device': {'refPath': device_ref},
            'propertyName': prop_name,
            'value': val_str
        })

    def add_event_binding(self, src_device, src_event, dst_device, dst_func):
        return self.call_tool('ValkyrieToolset.DeviceToolset', 'AddEventBinding', {
            'sourceDevicePath': {'refPath': src_device},
            'sourceEvent': src_event,
            'targetDevicePath': {'refPath': dst_device},
            'targetFunction': dst_func
        })

    def save_all(self):
        print("[*] Saving all dirty assets to disk...")
        res = self.call_tool('editor_toolset.toolsets.asset.AssetTools', 'save_assets', {'asset_paths': []})
        print(f"[+] Assets saved successfully: {res}")
        return res

def build_level():
    client = UefnMcpClient()
    GROUND_Z = 1155.0

    # 1. Compile Verse
    client.build_verse()

    # Asset References
    VERSE_CORE = '/LastHorizon_Core/_Verse.core_health_device'
    VERSE_WAVE = '/LastHorizon_Core/_Verse.wave_controller_device'
    VERSE_ECONOMY = '/LastHorizon_Core/_Verse.currency_economy_device'
    VERSE_TELEPORT = '/LastHorizon_Core/_Verse.teleport_gate_device'
    VERSE_GM = '/LastHorizon_Core/_Verse.game_manager_device'

    CREATIVE_BUTTON = '/CreativeCoreDevices/SetupAssets/PID_Device_Button.PID_Device_Button'
    CREATIVE_TELEPORTER = '/CreativeCoreDevices/SetupAssets/PID_Device_Teleporter.PID_Device_Teleporter'
    CREATIVE_SPAWNER = '/CRD_PlayerSpawn/ItemDefinitions/PID_Device_PlayerSpawnPad.PID_Device_PlayerSpawnPad'
    CREATIVE_GRANTER = '/CreativeCoreDevices/SetupAssets/PID_Device_ItemGranter.PID_Device_ItemGranter'
    CREATIVE_DEIMOS = '/CR_Legacy/Playsets/PID_CP_Devices_DeimosSpawner.PID_CP_Devices_DeimosSpawner'
    CREATIVE_ENDGAME = '/CRD_GameEnd/SetupAssets/PID_Device_EndGame_V2.PID_Device_EndGame_V2'

    placed = {}

    print("\n=======================================================")
    print("  PHASE 1: Building Sanctuary Zone (Center 0, 0)")
    print("=======================================================")
    
    # Core Health Device
    print("[1/5] Placing Zero Matrix Core...")
    placed['core_actor'] = client.place_device(VERSE_CORE, 0, 0, GROUND_Z)
    placed['core_subobject'] = f"{placed['core_actor']}.core_health_device_0"
    print(f"  -> Core Actor: {placed['core_actor']}")

    # Game Manager Device
    print("[2/5] Placing Game Manager Device...")
    placed['gm_actor'] = client.place_device(VERSE_GM, 0, -200, GROUND_Z)
    placed['gm_subobject'] = f"{placed['gm_actor']}.game_manager_device_0"
    print(f"  -> GM Actor: {placed['gm_actor']}")

    # Wave Controller Device
    print("[3/5] Placing Wave Controller Device...")
    placed['wave_actor'] = client.place_device(VERSE_WAVE, 0, -100, GROUND_Z)
    placed['wave_subobject'] = f"{placed['wave_actor']}.wave_controller_device_0"
    print(f"  -> Wave Actor: {placed['wave_actor']}")

    # Economy Device
    print("[4/5] Placing Currency Economy Device...")
    placed['economy_actor'] = client.place_device(VERSE_ECONOMY, 250, -100, GROUND_Z)
    placed['economy_subobject'] = f"{placed['economy_actor']}.currency_economy_device_0"
    print(f"  -> Economy Actor: {placed['economy_actor']}")

    # Teleport Gate Device
    print("[5/5] Placing Teleport Gate Device...")
    placed['teleport_gate_actor'] = client.place_device(VERSE_TELEPORT, -250, -100, GROUND_Z)
    placed['teleport_gate_subobject'] = f"{placed['teleport_gate_actor']}.teleport_gate_device_0"
    print(f"  -> Teleport Gate Actor: {placed['teleport_gate_actor']}")

    # 4 Player Spawn Pads
    print("\nPlacing 4 Player Spawn Pads (North-facing)...")
    spawn_coords = [(-300, -600), (-100, -600), (100, -600), (300, -600)]
    for i, (sx, sy) in enumerate(spawn_coords, 1):
        sp_ref = client.place_device(CREATIVE_SPAWNER, sx, sy, GROUND_Z, yaw=90.0)
        placed[f'player_spawner_{i}'] = sp_ref
        print(f"  -> Spawner {i} at ({sx}, {sy}): {sp_ref}")

    # End Game Device
    print("\nPlacing End Game Device...")
    placed['end_game'] = client.place_device(CREATIVE_ENDGAME, 0, -800, GROUND_Z)
    print(f"  -> End Game Device: {placed['end_game']}")

    print("\n=======================================================")
    print("  PHASE 2: Building East Wing - Weapon Forge & Logistics")
    print("=======================================================")
    
    # 3 Upgrade & Repair Buttons
    print("Placing Weapon Forge & Repair Interaction Buttons...")
    placed['btn_weapon_upgrade'] = client.place_device(CREATIVE_BUTTON, 450, 0, GROUND_Z, yaw=270.0)
    placed['btn_core_repair'] = client.place_device(CREATIVE_BUTTON, 450, 200, GROUND_Z, yaw=270.0)
    placed['btn_shield_upgrade'] = client.place_device(CREATIVE_BUTTON, 450, 400, GROUND_Z, yaw=270.0)
    print(f"  -> Weapon Upgrade Btn: {placed['btn_weapon_upgrade']}")
    print(f"  -> Core Repair Btn: {placed['btn_core_repair']}")
    print(f"  -> Shield Upgrade Btn: {placed['btn_shield_upgrade']}")

    # 3 Weapon Tier Item Granters
    print("Placing T1 / T2 / T3 Item Granters...")
    placed['granter_t1'] = client.place_device(CREATIVE_GRANTER, 600, 0, GROUND_Z)
    placed['granter_t2'] = client.place_device(CREATIVE_GRANTER, 600, 200, GROUND_Z)
    placed['granter_t3'] = client.place_device(CREATIVE_GRANTER, 600, 400, GROUND_Z)
    print(f"  -> T1 Granter: {placed['granter_t1']}")
    print(f"  -> T2 Granter: {placed['granter_t2']}")
    print(f"  -> T3 Granter: {placed['granter_t3']}")

    print("\n=======================================================")
    print("  PHASE 3: Building West Wing - Farm Room & Portal")
    print("=======================================================")
    
    # Sanctuary Departure & Arrival
    placed['btn_farm_enter'] = client.place_device(CREATIVE_BUTTON, -450, 0, GROUND_Z, yaw=90.0)
    placed['tp_farm_depart'] = client.place_device(CREATIVE_TELEPORTER, -550, 0, GROUND_Z)
    placed['tp_base_return'] = client.place_device(CREATIVE_TELEPORTER, -550, 200, GROUND_Z)
    print(f"  -> Farm Portal Enter Button: {placed['btn_farm_enter']}")
    print(f"  -> Departure Teleporter: {placed['tp_farm_depart']}")
    print(f"  -> Sanctuary Return Teleporter: {placed['tp_base_return']}")

    # Isolated Farm Room at (15000, 15000)
    FARM_X, FARM_Y = 15000, 15000
    print(f"\nConstructing Isolated Farm Room at ({FARM_X}, {FARM_Y})...")
    placed['tp_farm_arrival'] = client.place_device(CREATIVE_TELEPORTER, FARM_X, FARM_Y, GROUND_Z)
    placed['btn_farm_exit'] = client.place_device(CREATIVE_BUTTON, FARM_X, FARM_Y - 400, GROUND_Z, yaw=180.0)
    placed['tp_farm_return_src'] = client.place_device(CREATIVE_TELEPORTER, FARM_X, FARM_Y - 500, GROUND_Z)
    placed['farm_spawner_1'] = client.place_device(CREATIVE_DEIMOS, FARM_X - 300, FARM_Y + 400, GROUND_Z)
    placed['farm_spawner_2'] = client.place_device(CREATIVE_DEIMOS, FARM_X + 300, FARM_Y + 400, GROUND_Z)
    print(f"  -> Farm Arrival Teleporter: {placed['tp_farm_arrival']}")
    print(f"  -> Farm Early Exit Button: {placed['btn_farm_exit']}")
    print(f"  -> Farm Return Teleporter: {placed['tp_farm_return_src']}")
    print(f"  -> Farm Fiend Spawners: 2x placed")

    # Wire Farm Teleport events
    print("Wiring Farm Portal Event Bindings...")
    client.add_event_binding(placed['btn_farm_enter'], 'On Interact', placed['tp_farm_depart'], 'Teleport')
    client.add_event_binding(placed['btn_farm_exit'], 'On Interact', placed['tp_farm_return_src'], 'Teleport')

    print("\n=======================================================")
    print("  PHASE 4: Building North Corridor - Monster Spawners")
    print("=======================================================")
    
    lane_spawners = []
    print("Placing 3-Lane Corridor Fiend Spawners (3500m North)...")
    for i, lx in enumerate([-600, 0, 600], 1):
        sp = client.place_device(CREATIVE_DEIMOS, lx, 3500, GROUND_Z, yaw=180.0)
        placed[f'lane_spawner_{i}'] = sp
        lane_spawners.append(sp)
        print(f"  -> Lane Spawner {i} at ({lx}, 3500): {sp}")

    # Elite Boss Spawner (4500m North)
    print("Placing Elite Boss Spawner (4500m North)...")
    placed['boss_spawner'] = client.place_device(CREATIVE_DEIMOS, 0, 4500, GROUND_Z, yaw=180.0)
    print(f"  -> Boss Spawner: {placed['boss_spawner']}")

    # Bonus Carnival Spawner (2500m North)
    print("Placing Carnival Gold Bonus Spawner (2500m North)...")
    placed['bonus_spawner'] = client.place_device(CREATIVE_DEIMOS, 0, 2500, GROUND_Z, yaw=180.0)
    print(f"  -> Carnival Bonus Spawner: {placed['bonus_spawner']}")

    print("\n=======================================================")
    print("  PHASE 5: Configuring Verse Device Cross-References")
    print("=======================================================")

    # 1. Wire game_manager_device
    print("[*] Linking game_manager_device...")
    client.set_device_property(placed['gm_actor'], 'coreHealthDevice', {'refPath': placed['core_subobject']})
    client.set_device_property(placed['gm_actor'], 'waveControllerDevice', {'refPath': placed['wave_subobject']})
    client.set_device_property(placed['gm_actor'], 'economyDevice', {'refPath': placed['economy_subobject']})
    client.set_device_property(placed['gm_actor'], 'initialCountdownSeconds', 30.0)

    # 2. Wire currency_economy_device
    print("[*] Linking currency_economy_device...")
    client.set_device_property(placed['economy_actor'], 'coreHealthDevice', {'refPath': placed['core_subobject']})
    client.set_device_property(placed['economy_actor'], 'startingGold', 500)
    client.set_device_property(placed['economy_actor'], 'tier2UpgradeCost', 1500)
    client.set_device_property(placed['economy_actor'], 'tier3UpgradeCost', 4000)
    client.set_device_property(placed['economy_actor'], 'repairCost', 500)
    client.set_device_property(placed['economy_actor'], 'shieldUpgradeCost', 1000)

    # 3. Wire teleport_gate_device
    print("[*] Linking teleport_gate_device...")
    client.set_device_property(placed['teleport_gate_actor'], 'coreHealthDevice', {'refPath': placed['core_subobject']})
    client.set_device_property(placed['teleport_gate_actor'], 'ticketCost', 100)
    client.set_device_property(placed['teleport_gate_actor'], 'maxDurationSeconds', 45.0)

    # 4. Wire core_health_device
    print("[*] Configuring core_health_device baseline values...")
    client.set_device_property(placed['core_actor'], 'maxCoreHealth', 30000.0)
    client.set_device_property(placed['core_actor'], 'maxCoreShield', 10000.0)
    client.set_device_property(placed['core_actor'], 'shieldRegenPerSecond', 500.0)
    client.set_device_property(placed['core_actor'], 'shieldRegenDelay', 10.0)

    # 5. Save all assets to disk
    print("\n=======================================================")
    print("  PHASE 6: Saving All Level Assets (OFPA)")
    print("=======================================================")
    client.save_all()

    print("\n[SUCCESS] ALL LEVEL GENERATION TASKS COMPLETED SUCCESSFULLY!")
    print(f"Total devices generated: {len(placed)}")
    return placed

if __name__ == '__main__':
    build_level()
