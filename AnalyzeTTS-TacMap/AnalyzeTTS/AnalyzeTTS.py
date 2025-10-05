import json
import numpy as np
from lupa.lua54 import LuaRuntime
lua = LuaRuntime(unpack_returned_tuples=True)

lua.globals().loadfile('towns.lua')()

towns = lua.globals()['towns']

def find_map_transform(objects, preferred_names=None):
    # try preferred nicknames first
    preferred_names = preferred_names or ['TacMap', 'Tactical Map - Test', 'Tactical Map', 'TacticalMap']
    for name in preferred_names:
        for obj in objects:
            if obj.get('Nickname') == name and obj.get('Transform'):
                return obj['Transform']
    # fallback: pick object with a Transform and the largest scale (likely the map)
    candidates = [o for o in objects if o.get('Transform') and isinstance(o['Transform'], dict)]
    if not candidates:
        return None
    # choose by scaleX * scaleZ (map is usually much larger than tokens)
    def size_score(o):
        t = o['Transform']
        return abs(t.get('scaleX', 0)) * abs(t.get('scaleZ', 0))
    candidates.sort(key=size_score, reverse=True)
    return candidates[0]['Transform']

# Load TTS.json and collect map + city markers
cityCounters = []
with open('TTS.json') as ttsFile:
    ttsJson = json.load(ttsFile)
    objects = ttsJson.get('ObjectStates', [])
    print(f"Loaded TTS.json: {len(objects)} top-level objects")
    mapT = find_map_transform(objects, preferred_names=['TacMap', 'Tactical Map - Test', 'Tactical Map'])
    print("Map transform found:" if mapT else "Map transform NOT found")
    # debug: show candidate objects with Nickname/Tags
    for i,obj in enumerate(objects[:200]):
        nick = obj.get('Nickname')
        tags = obj.get('Tags')
        if nick or tags:
            print(f"obj[{i}] Nickname={nick!r} Tags={tags!r}")
    if not mapT:
        print("Warning: map transform not found in TTS.json. Aborting.")
    for obj in objects:
        # Use Nickname (not Tags) to find city markers
        nick = obj.get('Nickname')
        if not nick or not isinstance(nick, str) or nick.strip() == '':
            # no nickname -> skip
            continue
        name = nick.replace('\n', '').strip()
        matched = False
        # try exact match against towns.lua (Lua table)
        try:
            if towns[name] is not None:
                cityCounters.append((name, obj['Transform']))
                matched = True
        except Exception:
            pass
        if not matched:
            # try underscores -> spaces
            alt = name.replace('_', ' ')
            try:
                if towns[alt] is not None:
                    cityCounters.append((alt, obj['Transform']))
                    matched = True
            except Exception:
                pass
        if matched:
            print(f"Matched nickname -> town: '{name}'")
        else:
            print(f"Skipped nickname (no town): '{name}'")

def relativeOffset(objectTransform, mapTransform):
    x = (objectTransform['posX']-mapTransform['posX'])/mapTransform['scaleX']
    z = (objectTransform['posZ']-mapTransform['posZ'])/mapTransform['scaleZ']
    # undo saved rotation+mirror by swapping axes
    return (z, x)

def constructMatrix(counters, index):
    array = [[relativeOffset(c[1],mapT)[index],1] for c in counters]
    return np.matrix(array)

def getGeoLocations(counters, component):
    arr = []
    for c in counters:
        try:
            town = towns[c[0]]
        except Exception:
            town = None
        if not town:
            # should not happen because we filtered earlier; print to debug if it does
            print("WARNING: town not found during getGeoLocations:", c[0])
        else:
            # towns[...] returns a Lua table proxy; extract numeric component
            val = town[component]
            arr.append(val)
    return np.matrix(arr).transpose()

def solve(counters, index, component):
    if len(counters) < 2:
        raise ValueError("Need at least two city markers to compute scale+offset (found {}).".format(len(counters)))
    m = constructMatrix(counters, index)
    v = getGeoLocations(counters, component)
    if m.shape[0] != v.shape[0]:
        raise ValueError(f"Matrix row mismatch: m rows={m.shape[0]} v rows={v.shape[0]}; check that all counters have town coords")
    mT= m.transpose()
    M = np.matmul(mT,m)
    V = np.matmul(mT,v)
    R = np.linalg.solve(M,V)
    return (float(R.item(0)), float(R.item(1)))

# Validate we found map and enough city markers
if not mapT:
    raise SystemExit("Map transform not found in TTS.json; make sure the map object's Nickname matches expected names.")

print(f"Collected {len(cityCounters)} candidate city markers: {[c[0] for c in cityCounters]}")
if len(cityCounters) < 2:
    raise SystemExit("Insufficient city markers to compute mapping. Check Tags in TTS.json and towns.lua keys.")

easting = solve(cityCounters,0,'longitude')
northing = solve(cityCounters,1,'latitude')

def getBounds():
    with open('Bounds.json') as boundsFile:
        boundsJson = json.load(boundsFile)
        objects = boundsJson.get('ObjectStates', [])
        mapTransform = find_map_transform(objects, preferred_names=['TacMap', 'Tactical Map - Test', 'Tactical Map'])
        corners = {}
        if not mapTransform:
            print("Warning: map transform not found in Bounds.json")
        for object in objects:
            if object.get('Name') == 'Chess_Pawn' and object.get('Nickname'):
                if mapTransform:
                    corners[object['Nickname']] = relativeOffset(object['Transform'], mapTransform)
        return corners

bounds = getBounds()

with open('tts2lola.json','w') as out:
    data ={
        'easting':{'scale': easting[0], 'offset':easting[1]},
        'northing':{'scale': northing[0], 'offset':northing[1]},
        'bounds':bounds
        }
    json.dump(data, out, indent=4)
    
for cityCounter in cityCounters:
    pos = relativeOffset(cityCounter[1], mapT)
    geo = (pos[1]*easting[0]+easting[1], pos[0]*northing[0]+northing[1])
    try:
        town = towns[cityCounter[0]]
        lon = town['longitude']; lat = town['latitude']
    except Exception:
        lon = lat = None
    err = (None, None)
    if lon is not None and lat is not None:
        err = (geo[0] - lon, geo[1] - lat)
    print(f'{cityCounter[0]}: {geo}, ({err})')

