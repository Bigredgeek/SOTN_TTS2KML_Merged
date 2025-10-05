# SOTN_TTS2KML_Merged

A utility to automate the processing of Tabletop Simulator (TTS) save files from Song of the Nibelungs (SOTN) wargame sessions into KML map files. This tool coordinates the conversion of all three map layers (Tactical, Strategic, and Operational) from a single save file.

## Credits

This project is built upon the original TTS2KML scripts created by Gronank. The individual map conversion scripts, coordinate transformation system, and KML generation logic were all originally developed by Gronank. This merged version simply automates the process of running those scripts for all three map layers.

Original repositories by Gronank:
- [AnalyzeTTS](https://github.com/gronank/AnalyzeTTS)


## Overview

The process works by:
1. Taking a TTS save file containing three map layers (TacMap, StratMap, OpMap)
2. Using transformation data (tts2lola.json) to convert game coordinates to real-world coordinates
3. Generating KML files for each map layer with NATO and PACT unit positions
4. Combining all outputs into a single folder for easy web map integration

## How It Works

### Map Layers
Each map layer (Tactical, Strategic, Operational) has its own coordinate transformation system:
- **TacMap**: Highest detail, smallest area coverage
- **OpMap**: Medium detail, regional coverage
- **StratMap**: Strategic overview, largest area coverage

### Coordinate Transformation
Each folder contains a `tts2lola.json` file that defines:
- Map bounds in game coordinates
- Scale factors for converting to real-world coordinates
- Offset values for proper geo-positioning

### Unit Processing
The Python scripts:
1. Read the TTS save file JSON
2. Identify map objects and their transforms
3. Convert game coordinates to real-world coordinates
4. Sort units into NATO and PACT categories
5. Generate KML with proper styling and organization

## Requirements

- Python 3.x (must be added to system PATH)
- Folder structure must be maintained:
  ```
  SOTN_TTS2KML_Merged/
  ├── process_maps.bat
  ├── AnalyzeTTS-TacMap/TTS2KML/
  ├── AnalyzeTTS-StratMap/TTS2KML/
  └── AnalyzeTTS-OpMap/TTS2KML/
  ```

## Installation

1. Install Python:
   - Download from https://www.python.org/downloads/
   - **Important**: Check "Add Python to PATH" during installation
   - Restart your computer after installation
   - Verify by opening Command Prompt and typing: `python --version`

2. Verify Python PATH:
   If Python isn't recognized:
   - Open System Properties → Advanced → Environment Variables
   - Under "System Variables", find and select "Path"
   - Add Python paths (typically):
     ```
     C:\Users\[Username]\AppData\Local\Programs\Python\Python3x\
     C:\Users\[Username]\AppData\Local\Programs\Python\Python3x\Scripts\
     ```

## Usage

1. Place your TTS save file (e.g., `TS_Save_48.json`) in the main folder
2. Run `process_maps.bat`
3. Three KML files will be generated:
   - `TacMap.kml` - Tactical layer
   - `StratMap.kml` - Strategic layer
   - `OpMap.kml` - Operational layer

## Script Details

### process_maps.bat
- Finds JSON save files in the main folder
- Copies save file to each map's TTS2KML folder
- Runs the Python conversion scripts
- Collects generated KML files
- Cleans up temporary files

### TTS2KML.py (in each map folder)
- Reads map-specific transformation data
- Processes units based on map layer
- Generates KML with sorted layers for NATO/PACT/undeclared units as defined by the Tag in TTS
- Maintains unit styling and imagery

## Troubleshooting

1. **Python Path Issues**:
   - Verify Python installation: `python --version`
   - Check PATH environment variable
   - Try running Python scripts manually in each folder

2. **Save File Issues**:
   - Ensure save file is valid JSON
   - Check that map names match exactly: "TacMap", "StratMap", "OpMap"
   - Verify unit data contains required fields (Transform, Tags, etc.)

3. **KML Generation Issues**:
   - Check tts2lola.json files are present in each TTS2KML folder
   - Verify coordinate transformations are correct for each map
   - Ensure unit Tags are properly set for NATO/PACT sorting

## Notes

- The script preserves all original conversion functionality
- Each map layer maintains its own coordinate system
- KML files contain properly organized NATO and PACT folders
- Files are automatically cleaned up after processing
- Generated KMLs will overwrite existing files with the same names

## Technical Details

### Coordinate Transformation Process
1. Read unit position from TTS save (X,Y,Z coordinates)
2. Apply map-specific transformation from tts2lola.json
3. Convert to real-world coordinates (longitude/latitude)
4. Generate KML with proper positioning and styling

### Unit Organization
- Units are sorted by NATO/PACT tags
- Each unit maintains its custom imagery
- KML folders organize units by faction
- Scale and styling are preserved for web display
=======
Project for analyzing TTS files.

See TTS2KML project for exporting a TTS save file to KML.
>>>>>>> 4a7ef831ea277731c63b77cd0f5140eff3346bbe
