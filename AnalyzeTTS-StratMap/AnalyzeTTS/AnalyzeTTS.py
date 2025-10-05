import json
import numpy as np
from lupa.lua54 import LuaRuntime
lua = LuaRuntime(unpack_returned_tuples=True)

lua.globals().loadfile('towns.lua')()

towns = lua.globals()['towns']

def find_map_transform(objects, preferred_names=None):
    # try preferred nicknames first (strict: raise if none found)
    preferred_names = preferred_names or ['StratMap']
    for name in preferred_names:
        for obj in objects:
            if obj.get('Nickname') == name and obj.get('Transform'):
                return obj['Transform']

    # not found -> raise a clear error listing available objects
    available = [{'Nickname': o.get('Nickname'), 'Name': o.get('Name')} for o in objects]
    raise RuntimeError(f"Could not locate map with preferred nicknames {preferred_names}. Available objects: {available}")

# Load TTS.json and collect map + city markers
cityCounters = []
with open('TTS.json') as ttsFile:
    ttsJson = json.load(ttsFile)
    objects = ttsJson.get('ObjectStates', [])
    print(f"Loaded TTS.json: {len(objects)} top-level objects")
    mapT = find_map_transform(objects, preferred_names=['StratMap'])
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
    # Output raw offsets: return (x, z)
    return (x, z)

def constructMatrix(counters, index):
    positions = [relativeOffset(c[1], mapT) for c in counters]
    # 2D quadratic regression: [x^2, y^2, x*y, x, y, 1]
    array = [[pos[1]**2, pos[0]**2, pos[1]*pos[0], pos[1], pos[0], 1] for pos in positions]
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

# Top-level function for RANSAC robust fitting
def solve_ransac(counters, index, component, n_iter=100, threshold=0.01):
    # RANSAC for robust 2D quadratic fitting
    if len(counters) < 6:
        raise ValueError("Need at least six city markers to compute 2D quadratic transformation (found {}).".format(len(counters)))
    best_inliers = []
    best_coeffs = None
    positions = [relativeOffset(c[1], mapT) for c in counters]
    targets = []
    for c in counters:
        try:
            town = towns[c[0]]
            targets.append(town[component])
        except Exception:
            targets.append(None)
    for _ in range(n_iter):
        # Randomly sample 6 points
        idxs = np.random.choice(len(counters), 6, replace=False)
        sample_counters = [counters[i] for i in idxs]
        m = constructMatrix(sample_counters, index)
        v = getGeoLocations(sample_counters, component)
        try:
            mT = m.transpose()
            M = np.matmul(mT, m)
            V = np.matmul(mT, v)
            R = np.linalg.solve(M, V)
        except Exception:
            continue
        # Evaluate all points
        inliers = []
        for i, pos in enumerate(positions):
            x, y = pos[1], pos[0]
            pred = (
                R.item(0)*x**2 + R.item(1)*y**2 + R.item(2)*x*y + R.item(3)*x + R.item(4)*y + R.item(5)
            )
            target = targets[i]
            if target is None:
                continue
            if abs(pred - target) < threshold:
                inliers.append(i)
        if len(inliers) > len(best_inliers):
            best_inliers = inliers
            best_coeffs = tuple(float(R.item(i)) for i in range(6))
    # Refit using all inliers
    if best_inliers and len(best_inliers) >= 6:
        final_counters = [counters[i] for i in best_inliers]
        m = constructMatrix(final_counters, index)
        v = getGeoLocations(final_counters, component)
        mT = m.transpose()
        M = np.matmul(mT, m)
        V = np.matmul(mT, v)
        R = np.linalg.solve(M, V)
        return tuple(float(R.item(i)) for i in range(6))
    # fallback to least squares if RANSAC fails
    m = constructMatrix(counters, index)
    v = getGeoLocations(counters, component)
    mT = m.transpose()
    M = np.matmul(mT, m)
    V = np.matmul(mT, v)
    R = np.linalg.solve(M, V)
    return tuple(float(R.item(i)) for i in range(6))

def solve(counters, index, component):
    # Use RANSAC robust fitting
    return solve_ransac(counters, index, component, n_iter=200, threshold=0.01)

# Validate we found map and enough city markers
if not mapT:
    raise SystemExit("Map transform not found in TTS.json; make sure the map object's Nickname matches expected names.")

print(f"Collected {len(cityCounters)} candidate city markers: {[c[0] for c in cityCounters]}")
if len(cityCounters) < 6:
    raise SystemExit("Insufficient city markers to compute 2D quadratic mapping. Need at least 6.")

easting = solve(cityCounters, 0, 'longitude')  # (a, b, c, d, e, f)
northing = solve(cityCounters, 1, 'latitude')  # (a, b, c, d, e, f)

def getBounds():
    with open('Bounds.json') as boundsFile:
        boundsJson = json.load(boundsFile)
        objects = boundsJson.get('ObjectStates', [])
        mapTransform = find_map_transform(objects, preferred_names=['StratMap'])
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
    data = {
        'easting': {
            'a': easting[0], 'b': easting[1], 'c': easting[2],
            'd': easting[3], 'e': easting[4], 'f': easting[5]
        },
        'northing': {
            'a': northing[0], 'b': northing[1], 'c': northing[2],
            'd': northing[3], 'e': northing[4], 'f': northing[5]
        },
        'bounds': {
            'NorthEast': [bounds['NorthEast'][1], bounds['NorthEast'][0]],
            'SouthWest': [bounds['SouthWest'][1], bounds['SouthWest'][0]]
        }
    }
    json.dump(data, out, indent=4)
    
    for cityCounter in cityCounters:
        pos = relativeOffset(cityCounter[1], mapT)
        # Use 2D quadratic transformation for error reporting
        x, y = pos[1], pos[0]
        geo = (
            easting[0]*x**2 + easting[1]*y**2 + easting[2]*x*y + easting[3]*x + easting[4]*y + easting[5],
            northing[0]*x**2 + northing[1]*y**2 + northing[2]*x*y + northing[3]*x + northing[4]*y + northing[5]
        )
        try:
            town = towns[cityCounter[0]]
            lon = town['longitude']; lat = town['latitude']
        except Exception:
            lon = lat = None
        err = (None, None)
        if lon is not None and lat is not None:
            err = (geo[0] - lon, geo[1] - lat)
        print(f'{cityCounter[0]}: {geo}, ({err})')

