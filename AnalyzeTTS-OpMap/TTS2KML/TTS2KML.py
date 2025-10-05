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
                if ttsObjects['Nickname'] == 'OpMap':
                    self.mapTransform = ttsObjects['Transform']
                    break
        
    def relativeOffset(self, objectTransform):
        x = (objectTransform['posX']-self.mapTransform['posX'])/self.mapTransform['scaleX']
        z = (objectTransform['posZ']-self.mapTransform['posZ'])/self.mapTransform['scaleZ']
        # Flip east/west: mirror x, no rotation
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
        lat += -0.02 * x  # Adjust -0.04 as needed for best fit
        return (lon, lat)

def toKmlCoord(point):
    return f"{point[0]},{point[1]}"
def toKmlPoint(waypoint):
    return KML.Point(KML.coordinates(toKmlCoord(waypoint)))

def exportKml(doc, group):
    routeName = group.name
    linePoints = []
    wayPoints = []

    for wp in group.points[1:]:
        # Use the waypoint name as the style name, matching createKmlDoc logic
        style_name = wp.name.replace(' ', '')
        wayPoints.append(KML.Placemark(KML.name(wp.name), KML.styleUrl(f'#{style_name}'), toKmlPoint(wp)))
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
             continue
        if 'NATO' in unitTags:
            natoCounters.append(placemark)
        if 'WP' in unitTags:
            pactCounters.append(placemark)
        if 'Marker' in unitTags:
            neutralCounters.append(placemark)    
    
    natoFolder = KML.Folder(KML.name('NATO_OpMap'), *natoCounters)
    pactFolder = KML.Folder(KML.name('Pact_OpMap'), *pactCounters)
    neutralFolder = KML.Folder(KML.name('Undefined_Opmap'), *neutralCounters)
    
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


