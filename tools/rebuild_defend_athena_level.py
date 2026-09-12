import urllib.request
import json
import time

URL = 'http://127.0.0.1:8000/mcp'

class UefnClient:
    def __init__(self, url=URL):
        self.url = url
        self.session_id = None
        self.init()

    def rpc(self, method, params):
        payload = {'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params}
        headers = {'Content-Type': 'application/json'}
        if self.session_id:
            headers['Mcp-Session-Id'] = self.session_id
        req = urllib.request.Request(self.url, data=json.dumps(payload).encode('utf-8'), headers=headers)
        with urllib.request.urlopen(req) as resp:
            sess = resp.headers.get('Mcp-Session-Id')
            if sess:
                self.session_id = sess
            return json.loads(resp.read().decode('utf-8'))

    def init(self):
        res = self.rpc('initialize', {
            'protocolVersion': '2024-11-05',
            'capabilities': {},
            'clientInfo': {'name': 'AthenaHeroRebuilder', 'version': '1.0'}
        })
        print(f"[+] UEFN Connected. Session: {self.session_id}")

    def call_tool(self, toolset, tool, args):
        payload = {'toolset_name': toolset, 'tool_name': tool, 'arguments': args}
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

    def find_all_actors(self):
        res = self.call_tool('editor_toolset.toolsets.scene.SceneTools', 'find_actors', {'collision_channels': []})
        return res.get('returnValue', [])

    def remove_actor(self, ref):
        return self.call_tool('editor_toolset.toolsets.scene.SceneTools', 'remove_from_scene', {'actor': {'refPath': ref}})

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

    def add_event_binding(self, src_device, src_event, dst_device, dst_func):
        return self.call_tool('ValkyrieToolset.DeviceToolset', 'AddEventBinding', {
            'sourceDevicePath': {'refPath': src_device},
            'sourceEvent': src_event,
            'targetDevicePath': {'refPath': dst_device},
            'targetFunction': dst_func
        })

    def save_all(self):
        print("[*] Saving dirty level assets to disk...")
        res = self.call_tool('editor_toolset.toolsets.asset.AssetTools', 'save_assets', {'asset_paths': []})
        print(f"[+] Assets saved: {res}")
        return res

PROTECTED = {
    'FortWorldSettings', 'Brush', 'WorldDataLayers', 'BuoyancyManager',
    'MassVisualizer', 'DefaultPhysicsVolume', 'GameplayDebuggerPlayerManager',
    'ChaosDebugDrawActor', 'IslandSettings', 'BuilderGridPlane',
    'LevelBounds', 'WaterZone', 'WorldPartitionMiniMap', 'InstancedFoliageActor',
    'Cube_2', 'FortInspectorCameraCreative', 'LastHorizon_Core_SimulationEntityActor',
    'DSA_UEFN', 'SmartObjectSubsystemRenderingActor', 'AbstractNavData'
}

def should_delete(actor):
    path = actor.get('actorPath') or actor.get('refPath') or ''
    name = actor.get('name') or ''
    label = actor.get('label') or ''
    cls = actor.get('class', {}).get('refPath', '')
    native_cls = actor.get('nativeClass', {}).get('refPath', '')

    for prot in PROTECTED:
        if prot in name or prot in path:
            return False

    if 'VerseDevice' in path or 'VerseDevice' in cls or 'VerseDevice' in native_cls:
        return True

    keywords = [
        'Device', 'Spawner', 'Deimos', 'PlayerStart', 'Billboard',
        'Granter', 'Button', 'Teleport', 'Creature', 'EndGame',
        'Objective', 'TeamSettings'
    ]
    if any(k in path or k in name or k in label or k in cls or k in native_cls for k in keywords):
        return True

    return False

# Weapon Definitions mapped to Hero Classes and Tiers
WEAPONS = {
    'bm': [ # 疾风剑圣: 标准突击散弹枪 (从白到金)
        '/Game/Athena/Items/Weapons/WID_Shotgun_Standard_Athena_C_Ore_T03.WID_Shotgun_Standard_Athena_C_Ore_T03',
        '/Game/Athena/Items/Weapons/WID_Shotgun_Standard_Athena_UC_Ore_T03.WID_Shotgun_Standard_Athena_UC_Ore_T03',
        '/Game/Athena/Items/Weapons/WID_Shotgun_Standard_Athena_R_Ore_T03.WID_Shotgun_Standard_Athena_R_Ore_T03',
        '/Game/Athena/Items/Weapons/WID_Shotgun_Standard_Athena_VR_Ore_T03.WID_Shotgun_Standard_Athena_VR_Ore_T03',
        '/Game/Athena/Items/Weapons/WID_Shotgun_Standard_Athena_SR_Ore_T03.WID_Shotgun_Standard_Athena_SR_Ore_T03'
    ],
    'dr': [ # 黑暗游侠: 连发自动突击步枪 (从白到金)
        '/Game/Athena/Items/Weapons/WID_Assault_Auto_Athena_C_Ore_T02.WID_Assault_Auto_Athena_C_Ore_T02',
        '/Game/Athena/Items/Weapons/WID_Assault_Auto_Athena_UC_Ore_T03.WID_Assault_Auto_Athena_UC_Ore_T03',
        '/Game/Athena/Items/Weapons/WID_Assault_Auto_Athena_R_Ore_T03.WID_Assault_Auto_Athena_R_Ore_T03',
        '/Game/Athena/Items/Weapons/WID_Assault_Auto_Athena_VR_Ore_T03.WID_Assault_Auto_Athena_VR_Ore_T03',
        '/Game/Athena/Items/Weapons/WID_Assault_Auto_Athena_SR_Ore_T03.WID_Assault_Auto_Athena_SR_Ore_T03'
    ],
    'dh': [ # 恶魔猎手: 紧凑冲锋枪 -> 迈达斯神话鼓枪
        '/Game/Athena/Items/Weapons/WID_SMG_Compact_Athena_UC.WID_SMG_Compact_Athena_UC',
        '/Game/Athena/Items/Weapons/WID_SMG_Compact_Athena_R.WID_SMG_Compact_Athena_R',
        '/Game/Athena/Items/Weapons/WID_SMG_Compact_Athena_VR.WID_SMG_Compact_Athena_VR',
        '/Game/Athena/Items/Weapons/WID_SMG_Compact_Athena_SR.WID_SMG_Compact_Athena_SR',
        '/Game/Athena/Items/Weapons/Boss/WID_Boss_MidasDrumGun.WID_Boss_MidasDrumGun'
    ],
    'pal': [ # 圣殿骑士: 重型突击机枪 (从白到金)
        '/Game/Athena/Items/Weapons/WID_Assault_Heavy_Athena_C_Ore_T03.WID_Assault_Heavy_Athena_C_Ore_T03',
        '/Game/Athena/Items/Weapons/WID_Assault_Heavy_Athena_UC_Ore_T03.WID_Assault_Heavy_Athena_UC_Ore_T03',
        '/Game/Athena/Items/Weapons/WID_Assault_Heavy_Athena_R_Ore_T03.WID_Assault_Heavy_Athena_R_Ore_T03',
        '/Game/Athena/Items/Weapons/WID_Assault_Heavy_Athena_VR_Ore_T03.WID_Assault_Heavy_Athena_VR_Ore_T03',
        '/Game/Athena/Items/Weapons/WID_Assault_Heavy_Athena_SR_Ore_T03.WID_Assault_Heavy_Athena_SR_Ore_T03'
    ]
}

def main():
    client = UefnClient()
    GROUND_Z = 1155.0

    print("\n--- PHASE 0: Comprehensive Level Cleanup ---")
    actors = client.find_all_actors()
    to_delete = [a for a in actors if should_delete(a)]
    print(f"[*] Cleaning up {len(to_delete)} old dynamic gameplay actors...")
    for a in to_delete:
        ref = a.get('actorPath') or a.get('refPath')
        try:
            client.remove_actor(ref)
        except Exception:
            pass

    # Asset Definitions
    VERSE_HERO = '/LastHorizon_Core/_Verse.hero_rpg_device'
    VERSE_CORE = '/LastHorizon_Core/_Verse.core_health_device'
    VERSE_WAVE = '/LastHorizon_Core/_Verse.wave_controller_device'
    VERSE_ECONOMY = '/LastHorizon_Core/_Verse.currency_economy_device'
    VERSE_TELEPORT = '/LastHorizon_Core/_Verse.teleport_gate_device'
    VERSE_GM = '/LastHorizon_Core/_Verse.game_manager_device'

    CREATIVE_SPAWNER = '/CRD_PlayerSpawn/ItemDefinitions/PID_Device_PlayerSpawnPad.PID_Device_PlayerSpawnPad'
    CREATIVE_CREATURESPAWNER = '/CRD_Creatures/SetupAssets/PID_Device_CreatureSpawner_V2.PID_Device_CreatureSpawner_V2'
    CREATIVE_BUTTON = '/CreativeCoreDevices/SetupAssets/PID_Device_Button.PID_Device_Button'
    CREATIVE_TELEPORTER = '/CreativeCoreDevices/SetupAssets/PID_Device_Teleporter.PID_Device_Teleporter'
    CREATIVE_GRANTER = '/CreativeCoreDevices/SetupAssets/PID_Device_ItemGranter.PID_Device_ItemGranter'
    CREATIVE_BILLBOARD = '/CR_Legacy/Playsets/PID_CP_Devices_Billboard.PID_CP_Devices_Billboard'
    CREATIVE_TEAMSETTINGS = '/CreativeCoreDevices/SetupAssets/PID_Device_TeamSettings.PID_Device_TeamSettings'
    CREATIVE_OBJECTIVE = '/CreativeCoreDevices/SetupAssets/PID_Device_Objective.PID_Device_OBjective'
    CREATIVE_CREATUREMGR = '/CR_Legacy/Playsets/PID_CP_Devices_CreatureManager.PID_CP_Devices_CreatureManager'
    CREATIVE_ENDGAME = '/CRD_GameEnd/SetupAssets/PID_Device_EndGame_V2.PID_Device_EndGame_V2'

    placed = {}

    print("\n--- PHASE 1: Deploying Verse System Brains ---")
    placed['hero'] = client.place_device(VERSE_HERO, 0, -1100, GROUND_Z)
    placed['hero_sub'] = f"{placed['hero']}.hero_rpg_device_0"
    print(f"  [+] Hero RPG Device: {placed['hero']}")

    placed['core'] = client.place_device(VERSE_CORE, 0, 0, GROUND_Z)
    placed['core_sub'] = f"{placed['core']}.core_health_device_0"
    print(f"  [+] Core Health Device: {placed['core']}")

    placed['objective'] = client.place_device(CREATIVE_OBJECTIVE, 0, 0, GROUND_Z + 30)
    print(f"  [+] Core Objective Target: {placed['objective']}")

    placed['creature_mgr'] = client.place_device(CREATIVE_CREATUREMGR, 0, -350, GROUND_Z)

    placed['gm'] = client.place_device(VERSE_GM, 0, -100, GROUND_Z)
    placed['gm_sub'] = f"{placed['gm']}.game_manager_device_0"

    placed['wave'] = client.place_device(VERSE_WAVE, 0, -200, GROUND_Z)
    placed['wave_sub'] = f"{placed['wave']}.wave_controller_device_0"

    placed['economy'] = client.place_device(VERSE_ECONOMY, 150, -100, GROUND_Z)
    placed['economy_sub'] = f"{placed['economy']}.currency_economy_device_0"

    placed['teleport'] = client.place_device(VERSE_TELEPORT, -150, -100, GROUND_Z)
    placed['teleport_sub'] = f"{placed['teleport']}.teleport_gate_device_0"

    placed['end_game'] = client.place_device(CREATIVE_ENDGAME, 0, -800, GROUND_Z)

    # Team Settings (Infinite Ammo, Grant on Respawn)
    placed['team_settings'] = client.place_device(CREATIVE_TEAMSETTINGS, 0, -250, GROUND_Z)
    client.set_object_properties(placed['team_settings'], {
        'bGrantItemsOnRespawn': True,
        'bGrantAmmoWithWeapons': True,
        'bInfiniteAmmo': True
    })

    print("\n--- PHASE 2: Deploying Hero Selection Temple (0, -1500) ---")
    # All players spawn inside the Hero Selection Temple at Y = -1600
    placed['spawner_lobby_1'] = client.place_device(CREATIVE_SPAWNER, -150, -1600, GROUND_Z, yaw=90.0)
    placed['spawner_lobby_2'] = client.place_device(CREATIVE_SPAWNER, -50, -1600, GROUND_Z, yaw=90.0)
    placed['spawner_lobby_3'] = client.place_device(CREATIVE_SPAWNER, 50, -1600, GROUND_Z, yaw=90.0)
    placed['spawner_lobby_4'] = client.place_device(CREATIVE_SPAWNER, 150, -1600, GROUND_Z, yaw=90.0)

    # Frontline Arrival Teleporter (At Athena Core south gate, Y = -450)
    placed['tp_frontline'] = client.place_device(CREATIVE_TELEPORTER, 0, -450, GROUND_Z, yaw=90.0)

    # 4 Hero Pods facing South (yaw = 270)
    # Pod 1: 疾风剑圣 (Blade Master) at X = -450
    placed['btn_bm'] = client.place_device(CREATIVE_BUTTON, -450, -1350, GROUND_Z, yaw=270.0)
    placed['bb_bm'] = client.place_device(CREATIVE_BILLBOARD, -450, -1250, GROUND_Z + 50, yaw=270.0)
    client.set_object_properties(placed['bb_bm'], {
        'text': '【疾风剑圣】敏捷刺客\n初始神兵: 精炼近战散弹枪\n特色: 极速切后排、致命顺劈暴击\n[ 按 E 选定职业 ]',
        'textSize': 20
    })

    # Pod 2: 黑暗游侠 (Dark Ranger) at X = -150
    placed['btn_dr'] = client.place_device(CREATIVE_BUTTON, -150, -1350, GROUND_Z, yaw=270.0)
    placed['bb_dr'] = client.place_device(CREATIVE_BILLBOARD, -150, -1250, GROUND_Z + 50, yaw=270.0)
    client.set_object_properties(placed['bb_dr'], {
        'text': '【黑暗游侠】远程射手\n初始神兵: 连发自动突击步枪\n特色: 远程高频压制、穿云多重箭\n[ 按 E 选定职业 ]',
        'textSize': 20
    })

    # Pod 3: 恶魔猎手 (Demon Hunter) at X = 150
    placed['btn_dh'] = client.place_device(CREATIVE_BUTTON, 150, -1350, GROUND_Z, yaw=270.0)
    placed['bb_dh'] = client.place_device(CREATIVE_BILLBOARD, 150, -1250, GROUND_Z + 50, yaw=270.0)
    client.set_object_properties(placed['bb_dh'], {
        'text': '【恶魔猎手】突击狂暴\n初始神兵: 战术紧凑冲锋枪\n特色: 极速射速风暴、献祭吸血续航\n[ 按 E 选定职业 ]',
        'textSize': 20
    })

    # Pod 4: 圣殿骑士 (Paladin) at X = 450
    placed['btn_pal'] = client.place_device(CREATIVE_BUTTON, 450, -1350, GROUND_Z, yaw=270.0)
    placed['bb_pal'] = client.place_device(CREATIVE_BILLBOARD, 450, -1250, GROUND_Z + 50, yaw=270.0)
    client.set_object_properties(placed['bb_pal'], {
        'text': '【圣殿骑士】力量重装\n初始神兵: 重型突击机枪\n特色: 超厚护甲护盾、坚固阵线反伤\n[ 按 E 选定职业 ]',
        'textSize': 20
    })

    print("\n--- PHASE 3: Deploying Hero Progression Weapon Granters with Real Weapons ---")
    BASE_X, BASE_Y = 25000, 25000
    classes = ['bm', 'dr', 'dh', 'pal']
    for ci, cname in enumerate(classes):
        for tier_idx in range(5):
            tier = tier_idx + 1
            key = f"{cname}_t{tier}"
            gx = BASE_X + ci * 600
            gy = BASE_Y + tier * 300
            placed[key] = client.place_device(CREATIVE_GRANTER, gx, gy, GROUND_Z)
            
            # Configure Granter behavior
            client.set_object_properties(placed[key], {
                'bEquipGrantedItem': True,
                'grantCondition': 'Always',
                'onGrantAction': 'Clear Items'
            })

            # Populate actual weapon into pickupItemList.itemListData!
            wep_ref = WEAPONS[cname][tier_idx]
            item_data = [{
                'itemDefinition': {'refPath': wep_ref},
                'itemQuantity': 1,
                'templateObjectData': None,
                'itemOptionData': {'propertyOverrides': []},
                'itemVariantGuid': '00000000-0000-0000-0000-000000000000',
                'sourceItemVariantGuid': '00000000-0000-0000-0000-000000000000'
            }]
            comp_path = f"{placed[key]}.pickupItemList"
            client.set_object_properties(comp_path, {'itemListData': item_data})

    print("  [+] All 20 Weapon Granters armed with authentic Fortnite weapons!")

    print("\n--- PHASE 4: Wiring Event Bindings for Hero Selection ---")
    # Wire Button Press -> Teleport to frontline + Grant initial Tier 1 weapon!
    client.add_event_binding(placed['btn_bm'], 'On Interact', placed['tp_frontline'], 'Teleport')
    client.add_event_binding(placed['btn_bm'], 'On Interact', placed['bm_t1'], 'GrantItem')

    client.add_event_binding(placed['btn_dr'], 'On Interact', placed['tp_frontline'], 'Teleport')
    client.add_event_binding(placed['btn_dr'], 'On Interact', placed['dr_t1'], 'GrantItem')

    client.add_event_binding(placed['btn_dh'], 'On Interact', placed['tp_frontline'], 'Teleport')
    client.add_event_binding(placed['btn_dh'], 'On Interact', placed['dh_t1'], 'GrantItem')

    client.add_event_binding(placed['btn_pal'], 'On Interact', placed['tp_frontline'], 'Teleport')
    client.add_event_binding(placed['btn_pal'], 'On Interact', placed['pal_t1'], 'GrantItem')
    print("  [+] Button event bindings wired: Interact -> Arm Hero Weapon + Teleport to Frontline!")

    print("\n--- PHASE 5: Deploying 4 Incursion Camps (2800m) ---")
    # North Incursion (2800m)
    placed['spawner_n1'] = client.place_device(CREATIVE_CREATURESPAWNER, 0, 2800, GROUND_Z, yaw=270.0)
    placed['spawner_n2'] = client.place_device(CREATIVE_CREATURESPAWNER, -400, 2750, GROUND_Z, yaw=270.0)
    placed['spawner_n3'] = client.place_device(CREATIVE_CREATURESPAWNER, 400, 2750, GROUND_Z, yaw=270.0)

    # South Incursion (2800m)
    placed['spawner_s1'] = client.place_device(CREATIVE_CREATURESPAWNER, 0, -2800, GROUND_Z, yaw=90.0)
    placed['spawner_s2'] = client.place_device(CREATIVE_CREATURESPAWNER, -400, -2750, GROUND_Z, yaw=90.0)
    placed['spawner_s3'] = client.place_device(CREATIVE_CREATURESPAWNER, 400, -2750, GROUND_Z, yaw=90.0)

    # East Incursion (2800m)
    placed['spawner_e1'] = client.place_device(CREATIVE_CREATURESPAWNER, 2800, 0, GROUND_Z, yaw=180.0)
    placed['spawner_e2'] = client.place_device(CREATIVE_CREATURESPAWNER, 2750, -400, GROUND_Z, yaw=180.0)
    placed['spawner_e3'] = client.place_device(CREATIVE_CREATURESPAWNER, 2750, 400, GROUND_Z, yaw=180.0)

    # West Incursion (2800m)
    placed['spawner_w1'] = client.place_device(CREATIVE_CREATURESPAWNER, -2800, 0, GROUND_Z, yaw=0.0)
    placed['spawner_w2'] = client.place_device(CREATIVE_CREATURESPAWNER, -2750, -400, GROUND_Z, yaw=0.0)
    placed['spawner_w3'] = client.place_device(CREATIVE_CREATURESPAWNER, -2750, 400, GROUND_Z, yaw=0.0)

    # Boss & Bonus Spawners
    placed['spawner_boss'] = client.place_device(CREATIVE_CREATURESPAWNER, 0, 3100, GROUND_Z, yaw=270.0)
    placed['spawner_bonus'] = client.place_device(CREATIVE_CREATURESPAWNER, 0, 2000, GROUND_Z, yaw=270.0)

    spawner_keys = [
        'spawner_n1', 'spawner_n2', 'spawner_n3',
        'spawner_s1', 'spawner_s2', 'spawner_s3',
        'spawner_e1', 'spawner_e2', 'spawner_e3',
        'spawner_w1', 'spawner_w2', 'spawner_w3',
        'spawner_boss', 'spawner_bonus'
    ]
    for sk in spawner_keys:
        client.set_object_properties(placed[sk], {
            'activation Range': 35000,
            'despawn Range': 60000
        })

    print("\n--- PHASE 6: Deploying Athena Sanctuary & Training Room ---")
    # Central Athena Billboard
    placed['bb_center'] = client.place_device(CREATIVE_BILLBOARD, 0, 120, GROUND_Z + 50, yaw=270.0)
    client.set_object_properties(placed['bb_center'], {
        'text': '【零号矩阵·雅典娜圣域】\n生命值: 30,000 | 护盾: 10,000\n核心一旦破碎，防线彻底沦陷！',
        'textSize': 24
    })

    # NW Wing: Farm Portals
    placed['btn_farm_enter'] = client.place_device(CREATIVE_BUTTON, -300, 300, GROUND_Z, yaw=315.0)
    placed['tp_farm_depart'] = client.place_device(CREATIVE_TELEPORTER, -380, 380, GROUND_Z)
    placed['tp_base_return'] = client.place_device(CREATIVE_TELEPORTER, -220, 380, GROUND_Z)

    FARM_X, FARM_Y = 15000, 15000
    placed['tp_farm_arrival'] = client.place_device(CREATIVE_TELEPORTER, FARM_X, FARM_Y, GROUND_Z)
    placed['btn_farm_exit'] = client.place_device(CREATIVE_BUTTON, FARM_X, FARM_Y - 400, GROUND_Z, yaw=180.0)
    placed['tp_farm_return_src'] = client.place_device(CREATIVE_TELEPORTER, FARM_X, FARM_Y - 500, GROUND_Z)
    placed['farm_spawner_1'] = client.place_device(CREATIVE_CREATURESPAWNER, FARM_X - 300, FARM_Y + 400, GROUND_Z)
    placed['farm_spawner_2'] = client.place_device(CREATIVE_CREATURESPAWNER, FARM_X + 300, FARM_Y + 400, GROUND_Z)

    client.add_event_binding(placed['btn_farm_enter'], 'On Interact', placed['tp_farm_depart'], 'Teleport')
    client.add_event_binding(placed['btn_farm_exit'], 'On Interact', placed['tp_farm_return_src'], 'Teleport')

    print("\n--- PHASE 7: Wiring Verse Subsystem Properties ---")
    # 1. Wire game_manager_device
    try:
        client.set_device_property(placed['gm'], 'coreHealthDevice', {'refPath': placed['core_sub']})
        client.set_device_property(placed['gm'], 'waveControllerDevice', {'refPath': placed['wave_sub']})
        client.set_device_property(placed['gm'], 'economyDevice', {'refPath': placed['economy_sub']})
        client.set_device_property(placed['gm'], 'heroRpgDevice', {'refPath': placed['hero_sub']})
        client.set_device_property(placed['gm'], 'initialCountdownSeconds', 10.0)
        print("  [+] game_manager_device configured with HeroSelection state!")
    except Exception as e:
        print(f"  [!] game_manager_device warning: {e}")

    # 2. Wire wave_controller_device
    try:
        client.set_device_property(placed['wave'], 'heroRpgDevice', {'refPath': placed['hero_sub']})
        client.set_device_property(placed['wave'], 'maxWaves', 30)
        client.set_device_property(placed['wave'], 'defaultCombatDuration', 45.0)
        client.set_device_property(placed['wave'], 'defaultGreedWindow', 45.0)
        print("  [+] wave_controller_device configured with HeroRpg reward link!")
    except Exception as e:
        print(f"  [!] wave_controller_device warning: {e}")

    # 3. Wire core_health_device
    try:
        client.set_device_property(placed['core'], 'maxCoreHealth', 30000.0)
        client.set_device_property(placed['core'], 'maxCoreShield', 10000.0)
        client.set_device_property(placed['core'], 'shieldRegenPerSecond', 500.0)
        client.set_device_property(placed['core'], 'shieldRegenDelay', 10.0)
        print("  [+] core_health_device configured")
    except Exception as e:
        print(f"  [!] core_health_device warning: {e}")

    # 4. Configure IslandSettings Zero Build + Infinite Ammo
    island_ref = '/LastHorizon_Core/LastHorizon_Core.LastHorizon_Core:PersistentLevel.IslandSettings_0'
    try:
        client.set_object_properties(island_ref, {
            'allowBuilding': 'None',
            'bInfiniteAmmo': True,
            'bInfiniteMagazineAmmo': False
        })
        print("  [+] IslandSettings: Zero Build + Infinite Ammo configured")
    except Exception as e:
        print(f"  [!] IslandSettings warning: {e}")

    print("\n--- PHASE 8: Saving Dirty Level Assets ---")
    client.save_all()
    print(f"\n[SUCCESS] Hero Selection & Armed Defend Athena architecture fully deployed! Total elements: {len(placed)}")

if __name__ == '__main__':
    main()
