import json
from pykml.factory import KML_ElementMaker as KML
from lxml import etree

class GeoReferencedMap:
    def __init__(self, mapFile):
        with open('tts2lola.json') as transformFile:
            self.data = json.load(transformFile)
            
        with open(mapFile) as ttsFile:
            ttsState=json.load(ttsFile)
            for ttsObjects in ttsState['ObjectStates']:
                if ttsObjects['Nickname'] == 'TacMap':
                    self.mapTransform = ttsObjects['Transform']
                    break
        
    def relativeOffset(self, objectTransform):
        x = (objectTransform['posX']-self.mapTransform['posX'])/self.mapTransform['scaleX']
        z = (objectTransform['posZ']-self.mapTransform['posZ'])/self.mapTransform['scaleZ']
        # undo saved rotation+mirror by swapping axes
        return (z, x)
    
    def toLoLa(self, transform):
        x,y = self.relativeOffset(transform)
        if( x < self.data['bounds']['SouthWest'][0] or y < self.data['bounds']['SouthWest'][1] or x > self.data['bounds']['NorthEast'][0] or y > self.data['bounds']['NorthEast'][1]):
            return None
        easting = self.data['easting']
        northing = self.data['northing']
        return (x*easting['scale']+easting['offset'], y*northing['scale']+northing['offset'])

def toKmlCoord(point):
    return f"{point[0]},{point[1]}"
def toKmlPoint(waypoint):
    return KML.Point(KML.coordinates(toKmlCoord(waypoint)))

def exportKml(doc, group):
    routeName = group.name
    linePoints = []
    wayPoints = []

    for wp in group.points[1:]:
        wayPoints.append(KML.Placemark(KML.name(wp.name),KML.styleUrl(f'#{stylename}'), toKmlPoint(wp)))
        linePoints.append(toKmlCoord(wp))

    routeLine = KML.Placemark(KML.name(routeName), KML.LineString(KML.coordinates("\n".join(linePoints))))
    wpFolder= KML.Folder(KML.name(routeName), routeLine,*wayPoints)
    doc.Document.append(wpFolder)

def createKmlDoc(missionName, units):
    styles = []
    natoCounters = []
    pactCounters = []
    neutralCounters = []

    for unit in units:
        imagePath = unit[0]['CustomImage']['ImageURL']
        name = unit[0]['Nickname'].replace(' ','')
        style = KML.Style(
                KML.IconStyle(
                    KML.scale(1.7),
                    KML.Icon(
                        KML.href(imagePath)
                    ),
                ),
                id=name,
            )
        styles.append(style)
        key = name.replace(' ','')
        placemark = KML.Placemark(KML.name(name),KML.styleUrl(f'#{key}'), toKmlPoint(unit[1]))
        unitTags = unit[0].get('Tags')
        if not unitTags:
             neutralCounters.append(placemark)
             continue
        if 'NATO' in unitTags:
            natoCounters.append(placemark)
        if 'WP' in unitTags:
            pactCounters.append(placemark)
        if 'Marker' in unitTags:
            neutralCounters.append(placemark)    
    
    natoFolder = KML.Folder(KML.name('NATO_TacMap'), *natoCounters)
    pactFolder = KML.Folder(KML.name('Pact_TacMap'), *pactCounters)
    neutralFolder = KML.Folder(KML.name('Undefined_TacMap'), *neutralCounters)
    
    return KML.kml(
        KML.Document(
            KML.Name(missionName),
            *styles,
            natoFolder,
            pactFolder,
            neutralFolder
        )
    )

path = 'SampleScenario.json'
crs = GeoReferencedMap(path)

with open(path) as ttsFile:
    data = json.load(ttsFile)

def is_hq_supply(obj):
    """Return True if object's LuaScript contains HQ Supply (case-insensitive)."""
    lua = obj.get('LuaScript') or obj.get('LuaScriptState') or ''
    if not isinstance(lua, str):
        return False
    return 'hq supply' in lua.lower()

units = []
for obj in data.get('ObjectStates', []):
    # skip HQ Supply tokens by lua-script marker
    if is_hq_supply(obj):
        continue

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
            # skip empty entries and HQ Supply tokens inside containers
            if not isinstance(c, dict) or is_hq_supply(c):
                continue
            # prefer contained object's Tags; fall back to contained Name
            tags = c.get('Tags') or []
            # normalize tags for case-insensitive matching
            tags_lower = [t.lower() for t in tags if isinstance(t, str)]
            # consider any contained object that has tags we're interested in
            if tags_lower:
                # create a shallow copy so we can assign a Transform for style/metadata lookup
                item = dict(c)
                # give the contained object the parent's transform so crs.toLoLa works
                item['Transform'] = parent_transform
                units.append((item, parent_pos))
   
doc = createKmlDoc('Sample', units)
with open('Sample.kml',"wb") as out:
        out.write(etree.tostring(doc, pretty_print=True, encoding="utf-8"))


