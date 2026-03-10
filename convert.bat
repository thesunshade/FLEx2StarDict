@echo off
setlocal enabledelayedexpansion

:: Check for arguments
if "%~1"=="" (
    echo Usage: %~nx0 ^<xhtml_file^> ^<dictionary_name^>
    echo Example: %~nx0 my_dictionary.xhtml "Sinhala Dictionary"
    exit /b 1
)

if "%~2"=="" (
    echo Error: Please provide a name for the final dictionary.
    exit /b 1
)

set "XHTML_FILE=%~1"
set "DICT_NAME=%~2"
set "JSON_FILE=%~n1.json"
set "LISTS_FILE=lists.xml"

:: --- Age Check for lists.xml ---
if exist "%LISTS_FILE%" (
    :: Use PowerShell to check if the file is older than 30 days
    powershell -Command "if ((Get-Date) - (Get-Item '%LISTS_FILE%').LastWriteTime -gt (New-TimeSpan -Days 30)) { exit 1 } else { exit 0 }"
    
    if !errorlevel! equ 1 (
        echo [WARNING] %LISTS_FILE% is older than 30 days.
        echo It is recommended to generate a fresh one from FLEx.
        set /p "choice=Do you want to continue anyway? (Y/N): "
        if /i "!choice!" neq "Y" (
            echo Processing cancelled by user.
            exit /b 0
        )
    )
) else (
    echo [INFO] %LISTS_FILE% not found. Variation generation will be limited.
)

echo.
echo --- Phase 1: XHTML to JSON ---
python xhtml-to-json.py "%XHTML_FILE%"
if %ERRORLEVEL% neq 0 (
    echo Error during Phase 1. Aborting.
    exit /b %ERRORLEVEL%
)

echo.
echo --- Phase 2: JSON to StarDict ---
python json-to-stardict.py "%JSON_FILE%" "%DICT_NAME%"
if %ERRORLEVEL% neq 0 (
    echo Error during Phase 2. Aborting.
    exit /b %ERRORLEVEL%
)

echo.
echo Done! Your dictionary is ready in the "%DICT_NAME%" folder.
