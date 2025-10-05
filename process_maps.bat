@echo off
setlocal EnableDelayedExpansion

REM Check for save file
dir /b *.json > temp.txt
set /p SAVE_FILE=<temp.txt
del temp.txt

if "%SAVE_FILE%"=="" (
    echo No JSON save files found!
    pause
    exit /b 1
)

echo Found save file: %SAVE_FILE%

REM Copy save file to each map folder
echo Copying save file to map folders...
copy "%SAVE_FILE%" "AnalyzeTTS-TacMap\TTS2KML\"
copy "%SAVE_FILE%" "AnalyzeTTS-StratMap\TTS2KML\"
copy "%SAVE_FILE%" "AnalyzeTTS-OpMap\TTS2KML\"

REM Process each map
echo Processing Tactical Map...
cd AnalyzeTTS-TacMap\TTS2KML
python TTS2KML.py "%SAVE_FILE%"
if errorlevel 1 (
    echo Error processing Tactical Map
    cd ..\..
    goto :error
)
cd ..\..

echo Processing Strategic Map...
cd AnalyzeTTS-StratMap\TTS2KML
python TTS2KML.py "%SAVE_FILE%"
if errorlevel 1 (
    echo Error processing Strategic Map
    cd ..\..
    goto :error
)
cd ..\..

echo Processing Operational Map...
cd AnalyzeTTS-OpMap\TTS2KML
python TTS2KML.py "%SAVE_FILE%"
if errorlevel 1 (
    echo Error processing Operational Map
    cd ..\..
    goto :error
)
cd ..\..

REM Copy KML files back to main folder
echo Collecting KML files...
if exist "AnalyzeTTS-TacMap\TTS2KML\*.kml" (
    copy "AnalyzeTTS-TacMap\TTS2KML\*.kml" "TacMap.kml"
) else (
    echo Warning: No KML file generated for Tactical Map
)

if exist "AnalyzeTTS-StratMap\TTS2KML\*.kml" (
    copy "AnalyzeTTS-StratMap\TTS2KML\*.kml" "StratMap.kml"
) else (
    echo Warning: No KML file generated for Strategic Map
)

if exist "AnalyzeTTS-OpMap\TTS2KML\*.kml" (
    copy "AnalyzeTTS-OpMap\TTS2KML\*.kml" "OpMap.kml"
) else (
    echo Warning: No KML file generated for Operational Map
)

REM Cleanup
echo Cleaning up...
del "AnalyzeTTS-TacMap\TTS2KML\%SAVE_FILE%"
del "AnalyzeTTS-StratMap\TTS2KML\%SAVE_FILE%"
del "AnalyzeTTS-OpMap\TTS2KML\%SAVE_FILE%"

echo Done! KML files have been generated.
pause
exit /b 0

:error
echo Script failed!
pause
exit /b 1