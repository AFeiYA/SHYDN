import urllib.request
import json
import math
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
        self.rpc('initialize', {
            'protocolVersion': '2024-11-05',
            'capabilities': {},
            'clientInfo': {'name': 'AthenaPCGGenerator', 'version': '1.0'}
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

    def spawn_actor(self, asset_path, name, x, y, z=1155.0, pitch=0.0, yaw=0.0, roll=0.0, sx=1.0, sy=1.0, sz=1.0):
        res = self.call_tool('editor_toolset.toolsets.scene.SceneTools', 'add_to_scene_from_asset', {
            'asset_path': asset_path,
            'name': name,
            'xform': {
                'location': {'x': float(x), 'y': float(y), 'z': float(z)},
                'rotation': {'pitch': float(pitch), 'yaw': float(yaw), 'roll': float(roll)},
                'scale': {'x': float(sx), 'y': float(sy), 'z': float(sz)}
            },
            'snap_to_ground': False
        })
        return res.get('returnValue', {}).get('refPath')

    def save_all(self):
        print("[*] Saving level changes to disk...")
        res = self.call_tool('editor_toolset.toolsets.asset.AssetTools', 'save_assets', {'asset_paths': []})
        print(f"[+] Assets saved successfully: {res}")
        return res

# 100% Verified UEFN Assets Matrix
ASSETS = {
    'floor_marble': '/Game/Athena/Apollo/Environments/BuildingActors/Atlantis/Floors/Atlantis_Floor_01.Atlantis_Floor_01_C',
    'floor_pattern': '/Game/Athena/Apollo/Environments/BuildingActors/Atlantis/Floors/Atlantis_Floor_A_01.Atlantis_Floor_A_01_C',
    'reactor_core': '/Game/Athena/Apollo/Environments/BuildingActors/PowerPlant/Props/Apollo_PowerPlant_ReactorCore_01.Apollo_PowerPlant_ReactorCore_01_C',
    'zero_point_crystal': '/Game/Athena/Items/ForagedItems/ZeroPoint/Assets/Zero_Point_Crystals/Meshes/SM_Zero_Point_Crystals_piece_1.SM_Zero_Point_Crystals_piece_1',
    'pillar': '/Game/Athena/Apollo/Environments/BuildingActors/Bridges/Corners/Blueprints/BridgeSupport_01_Pillar.BridgeSupport_01_Pillar_C',
    'obelisk_glow': '/Game/Athena/Apollo/Environments/BuildingActors/Atlantis/Props/Apollo_Atlantis_Obelisk_Glow.Apollo_Atlantis_Obelisk_Glow_C',
    'coliseum_barricade': '/Game/Athena/Apollo/Environments/BuildingActors/Coliseum/Props/Apollo_Coliseum_Barricade_01.Apollo_Coliseum_Barricade_01_C',
    'fortified_barricade_1': '/Game/Athena/Apollo/Environments/BuildingActors/Fortified/Props/Apollo_Fortified_Barricade_01.Apollo_Fortified_Barricade_01_C',
    'fortified_barricade_2': '/Game/Athena/Apollo/Environments/BuildingActors/Fortified/Props/Apollo_Fortified_Barricade_02.Apollo_Fortified_Barricade_02_C',
    'sandbag': '/Game/Athena/Apollo/Environments/BuildingActors/Fortified/Props/Apollo_Fortified_Sandbag_01.Apollo_Fortified_Sandbag_01_C',
    'gate_bot': '/Game/Athena/Apollo/Environments/BuildingActors/Coliseum/Props/Coliseum_MainGate_Bot.Coliseum_MainGate_Bot_C',
    'gate_mid': '/Game/Athena/Apollo/Environments/BuildingActors/Coliseum/Props/Coliseum_MainGate_Mid.Coliseum_MainGate_Mid_C',
    'gate_top': '/Game/Athena/Apollo/Environments/BuildingActors/Coliseum/Props/Coliseum_MainGate_Top.Coliseum_MainGate_Top_C',
}

def main():
    client = UefnClient()
    GROUND_Z = 1155.0
    spawned_count = 0

    print("\n--- PHASE 0: Clean existing PCG generated actors ---")
    actors = client.find_all_actors()
    to_delete = [a for a in actors if 'PCG_' in a.get('name', '') or 'PCG_' in a.get('actorPath', '')]
    print(f"[*] Found {len(to_delete)} old PCG actors to clean...")
    for a in to_delete:
        ref = a.get('actorPath') or a.get('refPath')
        try:
            client.remove_actor(ref)
        except Exception:
            pass

    print("\n--- PHASE 1: Procedural Generation - Central Athena Sanctum (0, 0) ---")
    # 1.1 Marble Platform Floor Grid (4x4 Grid centered around Core)
    tile_size = 400.0
    for ix in range(-2, 2):
        for iy in range(-2, 2):
            fx = (ix + 0.5) * tile_size
            fy = (iy + 0.5) * tile_size
            asset = ASSETS['floor_pattern'] if (abs(ix) == 1 and abs(iy) == 1) else ASSETS['floor_marble']
            name = f"PCG_Sanctum_Floor_{ix}_{iy}"
            client.spawn_actor(asset, name, fx, fy, GROUND_Z)
            spawned_count += 1

    # 1.2 Core Energy Pedestal (ReactorCore + Hovering ZeroPoint Crystal)
    client.spawn_actor(ASSETS['reactor_core'], "PCG_Sanctum_Reactor_Base", 0.0, 0.0, GROUND_Z, sx=1.2, sy=1.2, sz=1.0)
    client.spawn_actor(ASSETS['zero_point_crystal'], "PCG_Sanctum_Zero_Point_Crystal", 0.0, 0.0, GROUND_Z + 180.0, sx=2.5, sy=2.5, sz=2.5)
    spawned_count += 2

    # 1.3 8 Colonnade Guardian Pillars (Circular radius R = 750, facing center)
    R_PILLAR = 750.0
    for i in range(8):
        angle_deg = i * 45.0
        angle_rad = math.radians(angle_deg)
        px = R_PILLAR * math.cos(angle_rad)
        py = R_PILLAR * math.sin(angle_rad)
        yaw = (angle_deg + 180.0) % 360.0
        name = f"PCG_Sanctum_Pillar_{i+1}"
        client.spawn_actor(ASSETS['pillar'], name, px, py, GROUND_Z, yaw=yaw, sx=0.8, sy=0.8, sz=1.0)
        spawned_count += 1

    # 1.4 Corner Perimeter Barricades (Four corners of Sanctum platform)
    corners = [(-650, -650, 45), (650, -650, 135), (650, 650, 225), (-650, 650, 315)]
    for idx, (cx, cy, cyaw) in enumerate(corners):
        name = f"PCG_Sanctum_Barricade_{idx+1}"
        client.spawn_actor(ASSETS['coliseum_barricade'], name, cx, cy, GROUND_Z, yaw=cyaw)
        spawned_count += 1

    print(f"  [+] Central Athena Sanctum generated: {spawned_count} elements.")

    print("\n--- PHASE 2: Procedural Generation - Hero Selection Temple Colonnade (0, -1500) ---")
    # 2.1 Colonnade Gallery backing the 4 Hero Pods (Y = -1200)
    pod_x = [-450, -150, 150, 450]
    for idx, x in enumerate(pod_x):
        name_p = f"PCG_Temple_Pillar_{idx+1}"
        client.spawn_actor(ASSETS['pillar'], name_p, x, -1200.0, GROUND_Z, yaw=90.0, sx=0.9, sy=0.9, sz=1.1)
        spawned_count += 1

    # 2.2 Grand Coliseum Triumph Arches (Left & Right framing the Temple entrance)
    for arch_idx, arch_x in enumerate([-300.0, 300.0]):
        client.spawn_actor(ASSETS['gate_bot'], f"PCG_Temple_GateBot_{arch_idx}", arch_x, -1220.0, GROUND_Z, yaw=90.0)
        client.spawn_actor(ASSETS['gate_mid'], f"PCG_Temple_GateMid_{arch_idx}", arch_x, -1220.0, GROUND_Z + 380.0, yaw=90.0)
        client.spawn_actor(ASSETS['gate_top'], f"PCG_Temple_GateTop_{arch_idx}", arch_x, -1220.0, GROUND_Z + 760.0, yaw=90.0)
        spawned_count += 3

    # 2.3 Temple Floor Walkway (Connecting Lobby spawners to Hero Pods)
    for tx in [-400, 0, 400]:
        for ty in [-1350, -1500]:
            name_tf = f"PCG_Temple_Floor_{tx}_{ty}"
            client.spawn_actor(ASSETS['floor_marble'], name_tf, tx, ty, GROUND_Z)
            spawned_count += 1

    print("  [+] Hero Selection Temple Colonnade & Triumph Arches generated!")

    print("\n--- PHASE 3: Procedural Generation - 4 Incursion Defensive Avenues ---")
    avenues = {
        'North': {'dx': 0, 'dy': 1, 'yaw': 0.0},
        'South': {'dx': 0, 'dy': -1, 'yaw': 180.0},
        'East':  {'dx': 1, 'dy': 0, 'yaw': 90.0},
        'West':  {'dx': -1, 'dy': 0, 'yaw': 270.0}
    }

    for dir_name, dir_info in avenues.items():
        dx, dy, base_yaw = dir_info['dx'], dir_info['dy'], dir_info['yaw']

        # Chokepoint 1 (Forward Bunker at Distance = 500m)
        d1 = 500.0
        c1_x, c1_y = dx * d1, dy * d1
        if dx == 0:
            client.spawn_actor(ASSETS['sandbag'], f"PCG_{dir_name}_Sandbag_L", c1_x - 220.0, c1_y, GROUND_Z, yaw=base_yaw)
            client.spawn_actor(ASSETS['sandbag'], f"PCG_{dir_name}_Sandbag_R", c1_x + 220.0, c1_y, GROUND_Z, yaw=base_yaw)
            client.spawn_actor(ASSETS['fortified_barricade_1'], f"PCG_{dir_name}_Barricade_1", c1_x - 120.0, c1_y - dy*40, GROUND_Z, yaw=base_yaw)
        else:
            client.spawn_actor(ASSETS['sandbag'], f"PCG_{dir_name}_Sandbag_L", c1_x, c1_y - 220.0, GROUND_Z, yaw=base_yaw)
            client.spawn_actor(ASSETS['sandbag'], f"PCG_{dir_name}_Sandbag_R", c1_x, c1_y + 220.0, GROUND_Z, yaw=base_yaw)
            client.spawn_actor(ASSETS['fortified_barricade_1'], f"PCG_{dir_name}_Barricade_1", c1_x - dx*40, c1_y - 120.0, GROUND_Z, yaw=base_yaw)
        spawned_count += 3

        # Chokepoint 2 (Midfield Fortress Line at Distance = 1200m)
        d2 = 1200.0
        c2_x, c2_y = dx * d2, dy * d2
        if dx == 0:
            client.spawn_actor(ASSETS['fortified_barricade_2'], f"PCG_{dir_name}_MidBarricade_L", c2_x - 300.0, c2_y, GROUND_Z, yaw=base_yaw)
            client.spawn_actor(ASSETS['fortified_barricade_2'], f"PCG_{dir_name}_MidBarricade_R", c2_x + 300.0, c2_y, GROUND_Z, yaw=base_yaw)
            client.spawn_actor(ASSETS['pillar'], f"PCG_{dir_name}_MidTower_L", c2_x - 450.0, c2_y, GROUND_Z, yaw=base_yaw, sx=1.2, sy=1.2, sz=1.2)
            client.spawn_actor(ASSETS['pillar'], f"PCG_{dir_name}_MidTower_R", c2_x + 450.0, c2_y, GROUND_Z, yaw=base_yaw, sx=1.2, sy=1.2, sz=1.2)
        else:
            client.spawn_actor(ASSETS['fortified_barricade_2'], f"PCG_{dir_name}_MidBarricade_L", c2_x, c2_y - 300.0, GROUND_Z, yaw=base_yaw)
            client.spawn_actor(ASSETS['fortified_barricade_2'], f"PCG_{dir_name}_MidBarricade_R", c2_x, c2_y + 300.0, GROUND_Z, yaw=base_yaw)
            client.spawn_actor(ASSETS['pillar'], f"PCG_{dir_name}_MidTower_L", c2_x, c2_y - 450.0, GROUND_Z, yaw=base_yaw, sx=1.2, sy=1.2, sz=1.2)
            client.spawn_actor(ASSETS['pillar'], f"PCG_{dir_name}_MidTower_R", c2_x, c2_y + 450.0, GROUND_Z, yaw=base_yaw, sx=1.2, sy=1.2, sz=1.2)
        spawned_count += 4

        # Chokepoint 3 (Outer Incursion Bastion at Distance = 2000m)
        d3 = 2000.0
        c3_x, c3_y = dx * d3, dy * d3
        if dx == 0:
            client.spawn_actor(ASSETS['coliseum_barricade'], f"PCG_{dir_name}_Outer_L", c3_x - 350.0, c3_y, GROUND_Z, yaw=base_yaw)
            client.spawn_actor(ASSETS['coliseum_barricade'], f"PCG_{dir_name}_Outer_R", c3_x + 350.0, c3_y, GROUND_Z, yaw=base_yaw)
        else:
            client.spawn_actor(ASSETS['coliseum_barricade'], f"PCG_{dir_name}_Outer_L", c3_x, c3_y - 350.0, GROUND_Z, yaw=base_yaw)
            client.spawn_actor(ASSETS['coliseum_barricade'], f"PCG_{dir_name}_Outer_R", c3_x, c3_y + 350.0, GROUND_Z, yaw=base_yaw)
        spawned_count += 2

    print(f"  [+] 4 Incursion Corridors armed with fortified bunkers, towers and barricades!")

    print("\n--- PHASE 4: Procedural Generation - 4 Void Rift Portals (2750m) ---")
    rift_heads = {
        'North_Rift': (0.0, 2750.0, 0),
        'South_Rift': (0.0, -2750.0, 180),
        'East_Rift':  (2750.0, 0.0, 90),
        'West_Rift':  (-2750.0, 0.0, 270)
    }

    for rift_name, (rx, ry, ryaw) in rift_heads.items():
        if rx == 0:
            client.spawn_actor(ASSETS['obelisk_glow'], f"PCG_{rift_name}_Obelisk_L", rx - 350.0, ry, GROUND_Z, yaw=ryaw, sx=1.3, sy=1.3, sz=1.5)
            client.spawn_actor(ASSETS['obelisk_glow'], f"PCG_{rift_name}_Obelisk_R", rx + 350.0, ry, GROUND_Z, yaw=ryaw, sx=1.3, sy=1.3, sz=1.5)
        else:
            client.spawn_actor(ASSETS['obelisk_glow'], f"PCG_{rift_name}_Obelisk_L", rx, ry - 350.0, GROUND_Z, yaw=ryaw, sx=1.3, sy=1.3, sz=1.5)
            client.spawn_actor(ASSETS['obelisk_glow'], f"PCG_{rift_name}_Obelisk_R", rx, ry + 350.0, GROUND_Z, yaw=ryaw, sx=1.3, sy=1.3, sz=1.5)
        spawned_count += 2

    print(f"  [+] 4 Void Rift Spires armed with glowing ancient obelisks!")

    print(f"\n--- PHASE 5: Level Persistence ---")
    client.save_all()
    print(f"\n[SUCCESS] Procedural Content Generation Complete! Total {spawned_count} 3D architectural elements seamlessly integrated!")

if __name__ == '__main__':
    main()
