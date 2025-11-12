# AI Agent Instructions for SOTN_TTS2KML_Merged

## Project Overview
Converts Tabletop Simulator (TTS) save files from Red Strike wargame sessions into KML map files for visualization on map.army and Google Earth. Processes three map layers (TacMap, StratMap, OpMap) with different coordinate systems and scales.

## Architecture

### Three-Folder Structure
Each map layer has an identical folder structure under `AnalyzeTTS-{TacMap|StratMap|OpMap}/`:
- `AnalyzeTTS/` - Coordinate transformation calibration (generates `tts2lola.json`)
- `TTS2KML/` - KML generation from TTS save files
- `Import/` - Counter/unit import utilities (not actively used)

**Critical**: All three folders contain functionally identical code but operate on different map layers with different coordinate transformations.

### Data Flow
1. User places `TS_Save_*.json` in repo root
2. `process_maps.bat` copies JSON to each `TTS2KML/` subfolder
3. Each `TTS2KML.py` script:
   - Loads `tts2lola.json` (coordinate transformation parameters)
   - Finds map object by Nickname ('TacMap', 'StratMap', 'OpMap')
   - Converts TTS coordinates → real-world lat/long
   - Generates KML with Style/Placemark structure
4. Batch script copies generated `*.kml` files to repo root
5. Files archived to `Archived KML's/<user-specified-name>/`

## Critical Implementation Details

### KML Style ID Requirements (CRITICAL BUG ZONE)
**The #1 source of bugs**: KML `<Style id="">` and `<styleUrl>#id</styleUrl>` must match EXACTLY.

Current implementation in `createKmlDoc()` (lines 59-71 in each TTS2KML.py):
```python
name = unit[0]['Nickname'].replace(' ','')  # Only removes spaces
style = KML.Style(..., id=name)  # Style ID
key = name.replace(' ','')  # Redundant - already no spaces
placemark = KML.Placemark(KML.name(name), KML.styleUrl(f'#{key}'), ...)
```

**Known Issues**:
- **Empty nicknames cause `<Style id="">` with `<styleUrl>#</styleUrl>`** - KML validators reject this
- Special characters (`/`, `()`, `-`) are PRESERVED in both id and styleUrl (correct behavior for map.army)
- DO NOT add hash suffixes or sanitize special chars - map.army tolerates duplicates and special chars

**Validation**: Before modifying KML generation, verify:
1. No units have empty/whitespace-only nicknames in source JSON
2. `id` attribute and `styleUrl` text match exactly (including special chars)
3. Test on map.army, not just Google Earth (stricter validation)

### Batch Script File Selection Bug
`process_maps.bat` lines 69-77 use FOR loop to find generated KML:
```batch
for %%F in ("AnalyzeTTS-TacMap\TTS2KML\*.kml") do (
    if /I not "%%~nF"=="Sample" (
        set "TACMAP_SOURCE=%%~fF"
    )
)
```

**Bug**: Loop overwrites variable on each iteration, selecting LAST file alphabetically (excluding Sample.kml).
- If old cached `.kml` files exist alongside new ones, wrong file gets copied
- **Solution**: Delete old KML files before regenerating, or modify batch to sort by timestamp

### Coordinate Transformation System
Each map layer uses `tts2lola.json` with:
- TacMap: Simple linear transformation (scale + offset)
- StratMap/OpMap: 2D quadratic transformation (6 parameters each for easting/northing)

Formula in StratMap/OpMap (lines 33-41 in TTS2KML.py):
```python
lon = easting['a']*x² + easting['b']*y² + easting['c']*x*y + 
      easting['d']*x + easting['e']*y + easting['f']
```

**Never modify `tts2lola.json`** - it's calibrated using city reference points in `towns.lua`.

## Common Development Tasks

### Testing KML Files
```bash
# Check for empty style IDs
grep -n '<Style id="">' TacMap.kml

# Verify styleUrl matches
python -c "
from xml.etree import ElementTree as ET
root = ET.parse('TacMap.kml').getroot()
ns = '{http://www.opengis.net/kml/2.2}'
for pm in root.iter(ns+'Placemark'):
    name = pm.find(ns+'name').text
    style = pm.find(ns+'styleUrl').text
    print(f'{name:30} -> {style}')
" | head -20

# Upload to map.army for validation (ShareID in URL)
# https://www.map.army/?ShareID=XXXXXXX&UserType=RW-XXXXXXXX
```

### Regenerating KML After Code Changes
```bash
# Delete old cached files to avoid batch script bug
Remove-Item "AnalyzeTTS-TacMap\TTS2KML\*.kml" -Exclude "Sample.kml"
Remove-Item "AnalyzeTTS-StratMap\TTS2KML\*.kml" -Exclude "Sample.kml"
Remove-Item "AnalyzeTTS-OpMap\TTS2KML\*.kml" -Exclude "Sample.kml"

# Run batch script (prompts for archive name)
.\process_maps.bat
```

### Manual Python Execution (for debugging)
```bash
cd AnalyzeTTS-TacMap\TTS2KML
python TTS2KML.py "../../TS_Save_124.json"
```

## Code Patterns

### Unit Filtering (TacMap only)
TacMap excludes "HQ Supply" tokens by LuaScript marker:
```python
def is_hq_supply(obj):
    lua = obj.get('LuaScript', '') or ''
    return 'hq supply' in lua.lower()
```
StratMap/OpMap don't filter these.

### Container Handling
Units can be:
1. Top-level `Custom_Tile`/`Custom_Token` objects
2. Inside `ContainedObjects` array (bags, decks)

Both get parent's Transform for positioning (lines 130-145).

### Tag-Based Categorization
Units sorted by `Tags` array:
- `'NATO'` → NATO_TacMap folder
- `'WP'` → Pact_TacMap folder  
- `'Marker'` or no tags → Undefined_TacMap folder

**Quirk**: Units with no tags AND no 'Marker' tag go to neutral in TacMap, but get SKIPPED in StratMap/OpMap (line 90-91).

## File Organization

### What Gets Committed
- Python scripts in `AnalyzeTTS-*/TTS2KML/TTS2KML.py`
- Root `TacMap.kml`, `StratMap.kml`, `OpMap.kml`
- Archived KML folders under `Archived KML's/GT*/`

### What Gets Ignored (per .gitignore)
- Python bytecode (`__pycache__/`, `*.pyc`)
- Temporary test files (`test_*.py`, `check_*.py`)

## External Dependencies

### Python Packages
- `pykml` - KML generation (uses `lxml` backend)
- `lxml` - XML serialization with `pretty_print=True`

### Map Validation Services
- **map.army**: Stricter KML validation than Google Earth
  - Rejects empty style IDs
  - Requires exact styleUrl matches
  - Primary target for KML compatibility

## Recent Bug Fixes (Context for Future Issues)

### Nov 2024: styleUrl Slash Corruption
**Symptom**: Icons not loading on map.army, placemarks showing default pins.

**Root Cause**: Old cached KML files with incorrect styleUrl formatting (`#HQ3PzD` vs `#HQ/3PzD`).

**Fix**: Delete old KML files before regeneration. DO NOT strip `/` chars from nicknames.

**Lesson**: Always verify generated files in subfolders vs root vs archived copies match exactly.
