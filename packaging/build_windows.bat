@echo off
REM ==========================================================================
REM  TIS (Bangla Word Converter) - Windows build script
REM  Produces:
REM    release\TIS_Bangla_Word_Converter.exe                  (portable, single file)
REM    release\TIS_Bangla_Word_Converter_Portable.zip         (portable exe + portable.ini)
REM    release\TIS_Bangla_Word_Converter_Setup.exe            (installer, needs Inno Setup 6)
REM  Run from anywhere:  packaging\build_windows.bat
REM ==========================================================================
setlocal EnableExtensions
cd /d "%~dp0.."

where python >nul 2>nul || (echo [ERROR] Python 3.10+ is not on PATH. & exit /b 1)
python -c "import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)" || (echo [ERROR] Python 3.10 or newer is required. & exit /b 1)

if not exist .venv (
    echo [1/6] Creating virtual environment...
    python -m venv .venv || exit /b 1
)
call .venv\Scripts\activate.bat

echo [2/6] Installing dependencies...
python -m pip install --upgrade pip >nul
python -m pip install -r requirements-dev.txt || exit /b 1

echo [3/6] Running tests...
set QT_QPA_PLATFORM=offscreen
python -m pytest -q tests || (echo [ERROR] Tests failed - build stopped. & exit /b 1)

set QT_QPA_PLATFORM=
echo [4/6] Building installer folder build...
pyinstaller --noconfirm --clean packaging\tis_installer.spec || exit /b 1

echo [5/6] Building portable single-file exe...
pyinstaller --noconfirm packaging\tis_portable.spec || exit /b 1

if not exist release mkdir release
copy /y dist\TIS_Bangla_Word_Converter.exe release\ >nul
if exist release\portable rmdir /s /q release\portable
mkdir release\portable
copy /y dist\TIS_Bangla_Word_Converter.exe release\portable\ >nul
copy /y packaging\portable.ini release\portable\ >nul
copy /y LICENSE release\portable\LICENSE.txt >nul
copy /y README.md release\portable\ >nul
powershell -NoProfile -Command "Compress-Archive -Force -Path 'release\portable\*' -DestinationPath 'release\TIS_Bangla_Word_Converter_Portable.zip'"

echo [6/6] Building installer...
set "ISCC="
if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
if exist "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" set "ISCC=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
if not defined ISCC (
    echo [WARN] Inno Setup 6 not found - installer skipped.
    echo        Install it from https://jrsoftware.org/isinfo.php and run this script again.
    goto done
)
"%ISCC%" packaging\installer_config\TIS_Bangla_Word_Converter.iss || exit /b 1

:done
echo.
echo Build finished. Files are in the "release" folder:
dir /b release
endlocal
