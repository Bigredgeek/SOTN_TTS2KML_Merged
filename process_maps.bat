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

REM Prompt for archive folder name
echo.
set /p ARCHIVE_NAME=Enter archive folder name (e.g., GT3): 
if "%ARCHIVE_NAME%"=="" (
    echo No archive folder name provided. Exiting.
    pause
    exit /b 1
)
set ARCHIVE_DIR=Archived KML's\%ARCHIVE_NAME%
echo Archive folder will be: "%ARCHIVE_DIR%"
mkdir "%ARCHIVE_DIR%" 2>nul

REM Copy save file to each map folder
echo Copying save file to map folders...
copy "%SAVE_FILE%" "AnalyzeTTS-TacMap\TTS2KML\"
copy "%SAVE_FILE%" "AnalyzeTTS-StratMap\TTS2KML\"
copy "%SAVE_FILE%" "AnalyzeTTS-OpMap\TTS2KML\"

REM Clean up old KML files to avoid conflicts
echo Cleaning old KML files...
for %%F in ("AnalyzeTTS-TacMap\TTS2KML\*.kml") do (
    if /I not "%%~nF"=="Sample" (
        del "%%~fF"
    )
)
for %%F in ("AnalyzeTTS-StratMap\TTS2KML\*.kml") do (
    if /I not "%%~nF"=="Sample" (
        del "%%~fF"
    )
)
for %%F in ("AnalyzeTTS-OpMap\TTS2KML\*.kml") do (
    if /I not "%%~nF"=="Sample" (
        del "%%~fF"
    )
)

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
set "TACMAP_SOURCE="
for %%F in ("AnalyzeTTS-TacMap\TTS2KML\*.kml") do (
    if /I not "%%~nF"=="Sample" (
        set "TACMAP_SOURCE=%%~fF"
    )
)
if defined TACMAP_SOURCE (
    copy /Y "!TACMAP_SOURCE!" "TacMap.kml" >nul
    call :TrimKml "TacMap.kml"
) else (
    echo Warning: No KML file generated for Tactical Map
)

set "STRATMAP_SOURCE="
for %%F in ("AnalyzeTTS-StratMap\TTS2KML\*.kml") do (
    if /I not "%%~nF"=="Sample" (
        set "STRATMAP_SOURCE=%%~fF"
    )
)
if defined STRATMAP_SOURCE (
    copy /Y "!STRATMAP_SOURCE!" "StratMap.kml" >nul
    call :TrimKml "StratMap.kml"
) else (
    echo Warning: No KML file generated for Strategic Map
)

set "OPMAP_SOURCE="
for %%F in ("AnalyzeTTS-OpMap\TTS2KML\*.kml") do (
    if /I not "%%~nF"=="Sample" (
        set "OPMAP_SOURCE=%%~fF"
    )
)
if defined OPMAP_SOURCE (
    copy /Y "!OPMAP_SOURCE!" "OpMap.kml" >nul
    call :TrimKml "OpMap.kml"
) else (
    echo Warning: No KML file generated for Operational Map
)

REM Archive the generated KML files (and the source JSON) into the chosen folder
echo Archiving KML files to "%ARCHIVE_DIR%"...
if exist "TacMap.kml" (
    copy /Y "TacMap.kml" "%ARCHIVE_DIR%\TacMap.kml" >nul
) else (
    echo Warning: TacMap.kml not found in root; skipping archive copy
)
if exist "StratMap.kml" (
    copy /Y "StratMap.kml" "%ARCHIVE_DIR%\StratMap.kml" >nul
) else (
    echo Warning: StratMap.kml not found in root; skipping archive copy
)
if exist "OpMap.kml" (
    copy /Y "OpMap.kml" "%ARCHIVE_DIR%\OpMap.kml" >nul
) else (
    echo Warning: OpMap.kml not found in root; skipping archive copy
)
if exist "%SAVE_FILE%" (
    copy /Y "%SAVE_FILE%" "%ARCHIVE_DIR%\%SAVE_FILE%" >nul
)

REM Cleanup
echo Cleaning up...
del "AnalyzeTTS-TacMap\TTS2KML\%SAVE_FILE%"
del "AnalyzeTTS-StratMap\TTS2KML\%SAVE_FILE%"
del "AnalyzeTTS-OpMap\TTS2KML\%SAVE_FILE%"

REM Clean up generated KML files in subdirectories
for %%F in ("AnalyzeTTS-TacMap\TTS2KML\*.kml") do (
    if /I not "%%~nF"=="Sample" (
        del "%%~fF"
    )
)
for %%F in ("AnalyzeTTS-StratMap\TTS2KML\*.kml") do (
    if /I not "%%~nF"=="Sample" (
        del "%%~fF"
    )
)
for %%F in ("AnalyzeTTS-OpMap\TTS2KML\*.kml") do (
    if /I not "%%~nF"=="Sample" (
        del "%%~fF"
    )
)

echo Done! KML files have been generated.
pause
exit /b 0

:TrimKml
set "_trim_target=%~1"
if not defined _trim_target exit /b
if exist "%~1" (
    python -c "from pathlib import Path; p = Path(r'%~f1'); data = p.read_bytes().rstrip(b'\r\n\t '); p.write_bytes(data)"
)
exit /b

:error
echo Script failed!
pause
exit /b 1