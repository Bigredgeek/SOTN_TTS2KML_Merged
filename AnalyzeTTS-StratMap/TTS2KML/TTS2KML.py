import json
import sys
import os
from pykml.factory import KML_ElementMaker as KML
from lxml import etree

DEFAULT_ICON_SCALE = 1.7
NEUTRAL_ICON_SCALE = 1.25
HQ_SUPPLY_IMAGE_URL = "https://steamusercontent-a.akamaihd.net/ugc/958597478463059274/DE73B64E1B5C6F272EA3BEE5EF458E73E48FF03D/"
QUARTER_SCALE_IMAGE_URL = "https://steamusercontent-a.akamaihd.net/ugc/10144907398872417582/74701FE7D2FE1F8C465CD8B717764EDEC0C1BF6C/"
HQ_SUPPLY_ICON_SCALE = DEFAULT_ICON_SCALE / 2
QUARTER_ICON_SCALE = 0.75


def _normalize_url(url):
    if not isinstance(url, str):
        return ""
    return url.strip().rstrip("/").lower()


def has_hq_supply_script(obj):
    lua = obj.get('LuaScript') or obj.get('LuaScriptState') or ''
    if not isinstance(lua, str):
        return False
    return 'hq supply' in lua.lower()


def marker_matches_url(obj, target_url):
    custom_image = obj.get('CustomImage') or {}
    if not isinstance(custom_image, dict):
        return False
    image_url = custom_image.get('ImageURL') or custom_image.get('ImageSecondaryURL')
    return _normalize_url(image_url) == _normalize_url(target_url)


def is_hq_supply_marker(obj):
    return has_hq_supply_script(obj) and marker_matches_url(obj, HQ_SUPPLY_IMAGE_URL)


def is_quarter_scale_marker(obj):
    return marker_matches_url(obj, QUARTER_SCALE_IMAGE_URL)


def is_special_marker(obj):
    return is_hq_supply_marker(obj) or is_quarter_scale_marker(obj)


def icon_scale_for(obj):
    if is_hq_supply_marker(obj):
        return HQ_SUPPLY_ICON_SCALE
    if is_quarter_scale_marker(obj):
        return QUARTER_ICON_SCALE
    tags = obj.get('Tags') or []
    normalized_tags = {t.lower() for t in tags if isinstance(t, str)}
    if 'nato' in normalized_tags or 'wp' in normalized_tags:
        return DEFAULT_ICON_SCALE
    return NEUTRAL_ICON_SCALE

class GeoReferencedMap:
    def __init__(self, mapFile):
        with open('tts2lola.json') as transformFile:
            self.data = json.load(transformFile)
            
        with open(mapFile) as ttsFile:
            ttsState=json.load(ttsFile)
            for ttsObjects in ttsState['ObjectStates']:
                if ttsObjects['Nickname'] == 'StratMap':
                    self.mapTransform = ttsObjects['Transform']
                    break
        
    def relativeOffset(self, objectTransform):
        x = (objectTransform['posX']-self.mapTransform['posX'])/self.mapTransform['scaleX']
        z = (objectTransform['posZ']-self.mapTransform['posZ'])/self.mapTransform['scaleZ']
        # undo saved rotation+mirror by swapping axes
        return (z, x)
    
    def toLoLa(self, transform):
        x, y = self.relativeOffset(transform)
        if (
            x < self.data['bounds']['SouthWest'][0] or y < self.data['bounds']['SouthWest'][1] or
            x > self.data['bounds']['NorthEast'][0] or y > self.data['bounds']['NorthEast'][1]
        ):
            return None
        easting = self.data['easting']
        northing = self.data['northing']
        # 2D quadratic transformation: lon = a*x^2 + b*y^2 + c*x*y + d*x + e*y + f
        lon = (
            easting['a'] * x**2 + easting['b'] * y**2 + easting['c'] * x * y +
            easting['d'] * x + easting['e'] * y + easting['f']
        )
        lat = (
            northing['a'] * x**2 + northing['b'] * y**2 + northing['c'] * x * y +
            northing['d'] * x + northing['e'] * y + northing['f']
        )
        # Apply longitude-dependent latitude correction (tilt/shear)
        lat += 0.02 * x
        return (lon, lat)

def toKmlCoord(point):
    return f"{point[0]},{point[1]}"
def toKmlPoint(waypoint):
    return KML.Point(KML.coordinates(toKmlCoord(waypoint)))

def createKmlDoc(missionName, units):
    styles_by_id = {}
    natoCounters = []
    pactCounters = []
    neutralCounters = []

    for obj, position in units:
        custom_image = obj.get('CustomImage') or {}
        imagePath = custom_image.get('ImageURL') or custom_image.get('ImageSecondaryURL') or ''
        raw_name = obj.get('Nickname') or ''
        name = raw_name.replace(' ','')
        icon_scale = icon_scale_for(obj)
        existing_style = styles_by_id.get(name)
        if existing_style:
            current_scale = existing_style['scale']
            # prefer the most restrictive (smallest) scale encountered
            if icon_scale < current_scale:
                existing_style['scale'] = icon_scale
            # fill in image path if missing
            if not existing_style['href'] and imagePath:
                existing_style['href'] = imagePath
        else:
            styles_by_id[name] = {
                'href': imagePath,
                'scale': icon_scale,
            }

        placemark = KML.Placemark(KML.name(name),KML.styleUrl(f'#{name}'), toKmlPoint(position))
        unitTags = obj.get('Tags')
        if not unitTags:
             continue
        if 'NATO' in unitTags:
            natoCounters.append(placemark)
        if 'WP' in unitTags:
            pactCounters.append(placemark)
        if 'Marker' in unitTags:
            neutralCounters.append(placemark)    
    styles = []
    for style_id, data in styles_by_id.items():
        href = data['href']
        scale_value = data['scale']
        style = KML.Style(
            KML.IconStyle(
                KML.scale(scale_value),
                KML.Icon(
                    KML.href(href)
                ),
            ),
            id=style_id,
        )
        styles.append(style)

    natoFolder = KML.Folder(KML.name('NATO_StratMap'), *natoCounters)
    pactFolder = KML.Folder(KML.name('Pact_StratMap'), *pactCounters)
    neutralFolder = KML.Folder(KML.name('Undefined_Stratmap'), *neutralCounters)
    
    return KML.kml(
        KML.Document(
            KML.Name(missionName),
            *styles,
            natoFolder,
            pactFolder,
            neutralFolder
        )
    )

# Get input file from command line or use default
if len(sys.argv) > 1:
    path = sys.argv[1]
else:
    path = 'SampleScenario.json'

crs = GeoReferencedMap(path)

with open(path) as ttsFile:
    data = json.load(ttsFile)

units = []
for obj in data.get('ObjectStates', []):
    # handle top-level custom tile/token items (units placed directly)
    if obj.get('Name') in ('Custom_Tile', 'Custom_Token'):
        pos = crs.toLoLa(obj.get('Transform', {}))
        if not pos:
            continue
        units.append((obj, pos))
        continue

    # handle containers that have contained objects (e.g. a bag holding markers)
    contained = obj.get('ContainedObjects') or []
    if contained:
        # use parent transform for contained items' world position
        parent_transform = obj.get('Transform', {})
        parent_pos = crs.toLoLa(parent_transform)
        if not parent_pos:
            continue
        for c in contained:
            # skip empty entries
            if not isinstance(c, dict):
                continue
            tags = c.get('Tags') or []
            if not tags and not is_special_marker(c):
                continue
            # create a shallow copy so we can assign a Transform for style/metadata lookup
            item = dict(c)
            # give the contained object the parent's transform so crs.toLoLa works
            item['Transform'] = parent_transform
            units.append((item, parent_pos))
   
# Generate output filename from input filename
base_name = os.path.splitext(os.path.basename(path))[0]
output_file = f'{base_name}.kml'

doc = createKmlDoc(base_name, units)
with open(output_file, "wb") as out:
    xml_bytes = etree.tostring(doc, pretty_print=True, encoding="utf-8")
    out.write(xml_bytes.rstrip(b"\r\n\t "))


