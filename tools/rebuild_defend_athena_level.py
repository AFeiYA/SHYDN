#!/usr/bin/env python3
"""
Last Horizon: Core Protocol - Complete Level Rebuilder (Defend Athena Alignment)
- 4-Direction Monster Incursion Camps (North, South, East, West at 2800m converging to center)
- Core Objective Device driving monster aggro directly to Center
- Creature Manager tuning speed, aggro, and rewards
- 4-Direction Player Spawners (North, South, East, West around Core at 500m)
- 4 Weapon Pedestals (Item Spawners) right beside each player spawner
- 5 Holographic Guidance Billboards with distinct mission and sector instructions
- Team Settings & Inventory: grant on respawn, infinite ammo
- IslandSettings: Zero Build (allowBuilding='None') and Infinite Ammo
- Diagonal Wings: Workshop (NE) and Teleport Portal (NW)
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
        print(f"[*] Connecting to UEFN MCP ({self.url})...")
        res = self.rpc('initialize', {
            'protocolVersion': '2024-11-05',
            'capabilities': {},
            'clientInfo': {'name': 'AthenaLevelRebuilder', 'version': '1.0'}
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

    def place_device(self, asset_ref, x, y, z=1155.0, yaw=0.0, pitch=0.0, roll=0.0):
        res = self.call_tool('ValkyrieToolset.DeviceToolset', 'PlaceDevice', {
            'assetPath': {'refPath': asset_ref},
            'transform': {
                'location': {'x': float(x), 'y': float(y), 'z': float(z)},
                'rotation': {'pitch': float(pitch), 'yaw': float(yaw), 'roll': float(roll)},
                'scale': {'x': 1.0, 'y': 1.0, 'z': 1.0}
            }
        })
        return res.get('returnValue', {}).get('refPath')

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

    def set_object_properties(self, actor_ref, props_dict):
        val_str = json.dumps(props_dict)
        return self.call_tool('editor_toolset.toolsets.object.ObjectTools', 'set_properties', {
            'instance': {'refPath': actor_ref},
            'values': val_str
        })

    def remove_actor(self, actor_ref):
        return self.call_tool('editor_toolset.toolsets.scene.SceneTools', 'remove_from_scene', {
            'actor': {'refPath': actor_ref}
        })

    def find_all_actors(self):
        res = self.call_tool('editor_toolset.toolsets.scene.SceneTools', 'find_actors', {
            'collision_channels': []
        })
        return res.get('returnValue', [])

    def add_event_binding(self, src_device, src_event, dst_device, dst_func):
        return self.call_tool('ValkyrieToolset.DeviceToolset', 'AddEventBinding', {
            'sourceDevicePath': {'refPath': src_device},
            'sourceEvent': src_event,
            'targetDevicePath': {'refPath': dst_device},
            'targetFunction': dst_func
        })

    def save_all(self):
        print("[*] Saving all dirty level assets to disk...")
        res = self.call_tool('editor_toolset.toolsets.asset.AssetTools', 'save_assets', {'asset_paths': []})
        print(f"[+] Assets saved: {res}")
        return res

def run():
    client = UefnMcpClient()
    GROUND_Z = 1155.0

    print("\n=======================================================")
    print("  PHASE 0: Cleaning Old Dynamic Gameplay Actors")
    print("=======================================================")
    actors = client.find_all_actors()
    to_delete = []
    for a in actors:
        label = a.get('label', '')
        ref = a.get('actorPath', '')
        cls = a.get('class', {}).get('refPath', '')
        if any(w in label for w in ['Creature Spawner', 'Player Spawner', 'Button', 'Item Granter', 'Item Spawner', 'Teleporter', 'Billboard', 'TeamSettings', 'Objective', 'CreatureManager']) or 'VerseDevice' in cls:
            to_delete.append(ref)

    print(f"[*] Found {len(to_delete)} gameplay actors to clean up...")
    for ref in to_delete:
        try:
            client.remove_actor(ref)
        except Exception as e:
            print(f"  Warning deleting {ref}: {e}")
    print("[+] Cleanup complete.")

    # Assets
    VERSE_CORE = '/LastHorizon_Core/_Verse.core_health_device'
    VERSE_WAVE = '/LastHorizon_Core/_Verse.wave_controller_device'
    VERSE_ECONOMY = '/LastHorizon_Core/_Verse.currency_economy_device'
    VERSE_TELEPORT = '/LastHorizon_Core/_Verse.teleport_gate_device'
    VERSE_GM = '/LastHorizon_Core/_Verse.game_manager_device'

    CREATIVE_SPAWNER = '/CRD_PlayerSpawn/ItemDefinitions/PID_Device_PlayerSpawnPad.PID_Device_PlayerSpawnPad'
    CREATIVE_DEIMOS = '/CR_Legacy/Playsets/PID_CP_Devices_DeimosSpawner.PID_CP_Devices_DeimosSpawner'
    CREATIVE_BUTTON = '/CreativeCoreDevices/SetupAssets/PID_Device_Button.PID_Device_Button'
    CREATIVE_TELEPORTER = '/CreativeCoreDevices/SetupAssets/PID_Device_Teleporter.PID_Device_Teleporter'
    CREATIVE_GRANTER = '/CreativeCoreDevices/SetupAssets/PID_Device_ItemGranter.PID_Device_ItemGranter'
    CREATIVE_ITEMSPAWNER = '/CreativeCoreDevices/SetupAssets/PID_Device_ItemSpawner.PID_Device_ItemSpawner'
    CREATIVE_BILLBOARD = '/CR_Legacy/Playsets/PID_CP_Devices_Billboard.PID_CP_Devices_Billboard'
    CREATIVE_TEAMSETTINGS = '/CreativeCoreDevices/SetupAssets/PID_Device_TeamSettings.PID_Device_TeamSettings'
    CREATIVE_OBJECTIVE = '/CreativeCoreDevices/SetupAssets/PID_Device_Objective.PID_Device_OBjective'
    CREATIVE_CREATUREMGR = '/CR_Legacy/Playsets/PID_CP_Devices_CreatureManager.PID_CP_Devices_CreatureManager'
    CREATIVE_ENDGAME = '/CRD_GameEnd/SetupAssets/PID_Device_EndGame_V2.PID_Device_EndGame_V2'

    placed = {}

    print("\n=======================================================")
    print("  PHASE 1: Core Sanctuary & Verse Brains (0, 0)")
    print("=======================================================")
    placed['core'] = client.place_device(VERSE_CORE, 0, 0, GROUND_Z)
    placed['core_sub'] = f"{placed['core']}.core_health_device_0"
    
    # Place Objective Device at Core to drive monster aggro inward!
    placed['objective'] = client.place_device(CREATIVE_OBJECTIVE, 0, 0, GROUND_Z + 30)
    print("  [+] Core Objective Target placed at (0, 0)")

    # Creature Manager to tune creature speed & damage
    placed['creature_mgr'] = client.place_device(CREATIVE_CREATUREMGR, 0, -350, GROUND_Z)
    print("  [+] Creature Manager placed at (0, -350)")

    placed['gm'] = client.place_device(VERSE_GM, 0, -100, GROUND_Z)
    placed['gm_sub'] = f"{placed['gm']}.game_manager_device_0"
    placed['wave'] = client.place_device(VERSE_WAVE, 0, -200, GROUND_Z)
    placed['wave_sub'] = f"{placed['wave']}.wave_controller_device_0"
    placed['economy'] = client.place_device(VERSE_ECONOMY, 150, -100, GROUND_Z)
    placed['economy_sub'] = f"{placed['economy']}.currency_economy_device_0"
    placed['teleport'] = client.place_device(VERSE_TELEPORT, -150, -100, GROUND_Z)
    placed['teleport_sub'] = f"{placed['teleport']}.teleport_gate_device_0"
    placed['end_game'] = client.place_device(CREATIVE_ENDGAME, 0, -800, GROUND_Z)

    # Team Settings & Inventory (Equip items on spawn, infinite ammo)
    placed['team_settings'] = client.place_device(CREATIVE_TEAMSETTINGS, 0, -250, GROUND_Z)
    client.set_object_properties(placed['team_settings'], {
        'bGrantItemsOnRespawn': True,
        'bGrantAmmoWithWeapons': True,
        'bInfiniteAmmo': True
    })

    print("\n=======================================================")
    print("  PHASE 2: 4-Direction Player Spawners & Weapon Pedestals")
    print("=======================================================")
    # 4 Player Spawners facing outward at radius 500m
    placed['player_north'] = client.place_device(CREATIVE_SPAWNER, 0, 500, GROUND_Z, yaw=90.0)
    placed['player_south'] = client.place_device(CREATIVE_SPAWNER, 0, -500, GROUND_Z, yaw=270.0)
    placed['player_east'] = client.place_device(CREATIVE_SPAWNER, 500, 0, GROUND_Z, yaw=0.0)
    placed['player_west'] = client.place_device(CREATIVE_SPAWNER, -500, 0, GROUND_Z, yaw=180.0)

    # 4 Weapon Item Spawners right beside each player spawner
    placed['item_north'] = client.place_device(CREATIVE_ITEMSPAWNER, 60, 500, GROUND_Z)
    placed['item_south'] = client.place_device(CREATIVE_ITEMSPAWNER, 60, -500, GROUND_Z)
    placed['item_east'] = client.place_device(CREATIVE_ITEMSPAWNER, 500, 60, GROUND_Z)
    placed['item_west'] = client.place_device(CREATIVE_ITEMSPAWNER, -500, 60, GROUND_Z)

    print("  [+] North Guard Post: Player Spawner (0, 500) + Weapon Station (60, 500)")
    print("  [+] South Guard Post: Player Spawner (0, -500) + Weapon Station (60, -500)")
    print("  [+] East Guard Post: Player Spawner (500, 0) + Weapon Station (500, 60)")
    print("  [+] West Guard Post: Player Spawner (-500, 0) + Weapon Station (-500, 60)")

    print("\n=======================================================")
    print("  PHASE 3: Holographic Guidance Billboards")
    print("=======================================================")
    # Center Core Billboard
    placed['bb_center'] = client.place_device(CREATIVE_BILLBOARD, 0, 120, GROUND_Z + 50, yaw=270.0)
    client.set_object_properties(placed['bb_center'], {
        'text': '【零号矩阵能量核心】\n生命值: 30,000 | 护盾: 10,000\n核心一旦被击毁，防线彻底沦陷！',
        'textSize': 24
    })

    # North Spawner Billboard
    placed['bb_north'] = client.place_device(CREATIVE_BILLBOARD, 0, 620, GROUND_Z + 50, yaw=90.0)
    client.set_object_properties(placed['bb_north'], {
        'text': '【北哨位·正面防线】\n怪物正从正北 2800m 裂隙集结，持枪迎战！',
        'textSize': 22
    })

    # South Spawner Billboard
    placed['bb_south'] = client.place_device(CREATIVE_BILLBOARD, 0, -620, GROUND_Z + 50, yaw=270.0)
    client.set_object_properties(placed['bb_south'], {
        'text': '【南哨位·防御裂隙】\n怪物正从正南 2800m 裂隙突入，誓死坚守！',
        'textSize': 22
    })

    # East Spawner Billboard
    placed['bb_east'] = client.place_device(CREATIVE_BILLBOARD, 620, 0, GROUND_Z + 50, yaw=0.0)
    client.set_object_properties(placed['bb_east'], {
        'text': '【东哨位·军备工坊区】\n击杀怪物收集金币，在东北侧升级高爆神兵！',
        'textSize': 22
    })

    # West Spawner Billboard
    placed['bb_west'] = client.place_device(CREATIVE_BILLBOARD, -620, 0, GROUND_Z + 50, yaw=180.0)
    client.set_object_properties(placed['bb_west'], {
        'text': '【西哨位·折跃枢纽】\n靠近西北侧传送门进入 45 秒限时打金房！',
        'textSize': 22
    })

    print("\n=======================================================")
    print("  PHASE 4: 4-Direction Monster Incursion Camps (2800m)")
    print("=======================================================")
    DIST = 2800.0
    # 1. NORTH CAMP (2800m North, marching South toward (0,0))
    print("[*] Placing North Incursion Camp (0, 2800)...")
    placed['spawner_n1'] = client.place_device(CREATIVE_DEIMOS, -350, DIST, GROUND_Z, yaw=270.0)
    placed['spawner_n2'] = client.place_device(CREATIVE_DEIMOS, 0, DIST, GROUND_Z, yaw=270.0)
    placed['spawner_n3'] = client.place_device(CREATIVE_DEIMOS, 350, DIST, GROUND_Z, yaw=270.0)

    # 2. SOUTH CAMP (2800m South, marching North toward (0,0))
    print("[*] Placing South Incursion Camp (0, -2800)...")
    placed['spawner_s1'] = client.place_device(CREATIVE_DEIMOS, -350, -DIST, GROUND_Z, yaw=90.0)
    placed['spawner_s2'] = client.place_device(CREATIVE_DEIMOS, 0, -DIST, GROUND_Z, yaw=90.0)
    placed['spawner_s3'] = client.place_device(CREATIVE_DEIMOS, 350, -DIST, GROUND_Z, yaw=90.0)

    # 3. EAST CAMP (2800m East, marching West toward (0,0))
    print("[*] Placing East Incursion Camp (2800, 0)...")
    placed['spawner_e1'] = client.place_device(CREATIVE_DEIMOS, DIST, -350, GROUND_Z, yaw=180.0)
    placed['spawner_e2'] = client.place_device(CREATIVE_DEIMOS, DIST, 0, GROUND_Z, yaw=180.0)
    placed['spawner_e3'] = client.place_device(CREATIVE_DEIMOS, DIST, 350, GROUND_Z, yaw=180.0)

    # 4. WEST CAMP (2800m West, marching East toward (0,0))
    print("[*] Placing West Incursion Camp (-2800, 0)...")
    placed['spawner_w1'] = client.place_device(CREATIVE_DEIMOS, -DIST, -350, GROUND_Z, yaw=0.0)
    placed['spawner_w2'] = client.place_device(CREATIVE_DEIMOS, -DIST, 0, GROUND_Z, yaw=0.0)
    placed['spawner_w3'] = client.place_device(CREATIVE_DEIMOS, -DIST, 350, GROUND_Z, yaw=0.0)

    # Special Boss & Carnival Spawners
    placed['spawner_boss'] = client.place_device(CREATIVE_DEIMOS, 0, 3800, GROUND_Z, yaw=270.0)
    placed['spawner_bonus'] = client.place_device(CREATIVE_DEIMOS, 0, 2000, GROUND_Z, yaw=270.0)

    print("\n=======================================================")
    print("  PHASE 5: Diagonal Wings - Forge (NE) & Teleport (NW)")
    print("=======================================================")
    # North-East Wing: Weapon Forge & Logistics
    placed['btn_weapon_upgrade'] = client.place_device(CREATIVE_BUTTON, 300, 300, GROUND_Z, yaw=225.0)
    placed['btn_core_repair'] = client.place_device(CREATIVE_BUTTON, 380, 220, GROUND_Z, yaw=225.0)
    placed['btn_shield_upgrade'] = client.place_device(CREATIVE_BUTTON, 220, 380, GROUND_Z, yaw=225.0)

    placed['granter_t1'] = client.place_device(CREATIVE_GRANTER, 450, 450, GROUND_Z)
    placed['granter_t2'] = client.place_device(CREATIVE_GRANTER, 480, 380, GROUND_Z)
    placed['granter_t3'] = client.place_device(CREATIVE_GRANTER, 380, 480, GROUND_Z)

    # North-West Wing: Farm Portal & Sanctuary Return
    placed['btn_farm_enter'] = client.place_device(CREATIVE_BUTTON, -300, 300, GROUND_Z, yaw=315.0)
    placed['tp_farm_depart'] = client.place_device(CREATIVE_TELEPORTER, -380, 380, GROUND_Z)
    placed['tp_base_return'] = client.place_device(CREATIVE_TELEPORTER, -220, 380, GROUND_Z)

    # Far Isolated Farm Room at (15000, 15000)
    FARM_X, FARM_Y = 15000, 15000
    placed['tp_farm_arrival'] = client.place_device(CREATIVE_TELEPORTER, FARM_X, FARM_Y, GROUND_Z)
    placed['btn_farm_exit'] = client.place_device(CREATIVE_BUTTON, FARM_X, FARM_Y - 400, GROUND_Z, yaw=180.0)
    placed['tp_farm_return_src'] = client.place_device(CREATIVE_TELEPORTER, FARM_X, FARM_Y - 500, GROUND_Z)
    placed['farm_spawner_1'] = client.place_device(CREATIVE_DEIMOS, FARM_X - 300, FARM_Y + 400, GROUND_Z)
    placed['farm_spawner_2'] = client.place_device(CREATIVE_DEIMOS, FARM_X + 300, FARM_Y + 400, GROUND_Z)

    # Wire Farm Portals
    client.add_event_binding(placed['btn_farm_enter'], 'On Interact', placed['tp_farm_depart'], 'Teleport')
    client.add_event_binding(placed['btn_farm_exit'], 'On Interact', placed['tp_farm_return_src'], 'Teleport')

    print("\n=======================================================")
    print("  PHASE 6: Wire Verse Properties & Configure Island")
    print("=======================================================")
    # 1. Wire game_manager_device
    client.set_device_property(placed['gm'], 'coreHealthDevice', {'refPath': placed['core_sub']})
    client.set_device_property(placed['gm'], 'waveControllerDevice', {'refPath': placed['wave_sub']})
    client.set_device_property(placed['gm'], 'economyDevice', {'refPath': placed['economy_sub']})
    client.set_device_property(placed['gm'], 'initialCountdownSeconds', 30.0)

    # 2. Wire currency_economy_device
    client.set_device_property(placed['economy'], 'coreHealthDevice', {'refPath': placed['core_sub']})
    client.set_device_property(placed['economy'], 'startingGold', 500)
    client.set_device_property(placed['economy'], 'tier2UpgradeCost', 1500)
    client.set_device_property(placed['economy'], 'tier3UpgradeCost', 4000)
    client.set_device_property(placed['economy'], 'repairCost', 500)
    client.set_device_property(placed['economy'], 'shieldUpgradeCost', 1000)

    # 3. Wire teleport_gate_device
    client.set_device_property(placed['teleport'], 'coreHealthDevice', {'refPath': placed['core_sub']})
    client.set_device_property(placed['teleport'], 'ticketCost', 100)
    client.set_device_property(placed['teleport'], 'maxDurationSeconds', 45.0)

    # 4. Wire core_health_device
    client.set_device_property(placed['core'], 'maxCoreHealth', 30000.0)
    client.set_device_property(placed['core'], 'maxCoreShield', 10000.0)
    client.set_device_property(placed['core'], 'shieldRegenPerSecond', 500.0)
    client.set_device_property(placed['core'], 'shieldRegenDelay', 10.0)

    # 5. Configure IslandSettings Zero Build + Infinite Ammo
    island_ref = '/LastHorizon_Core/LastHorizon_Core.LastHorizon_Core:PersistentLevel.IslandSettings_0'
    client.set_object_properties(island_ref, {
        'allowBuilding': 'None',
        'bInfiniteAmmo': True,
        'bInfiniteMagazineAmmo': False
    })

    print("\n=======================================================")
    print("  PHASE 7: Saving All Assets (OFPA)")
    print("=======================================================")
    client.save_all()
    print("[SUCCESS] Complete Defend Athena level architecture deployed!")
    print(f"Total devices generated: {len(placed)}")

if __name__ == '__main__':
    run()
