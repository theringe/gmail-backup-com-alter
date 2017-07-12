@echo off


::Set personal Path to the Apps:
set PythonEXE="D:\Dropbox\SYNC\Program\win32green\Portable Python 2.7.3.1\App\python.exe"
set PYTHONHOME=D:\Dropbox\SYNC\Program\win32green\Portable Python 2.7.3.1\App
set SevenZipEXE="D:\Dropbox\SYNC\Program\win32paf\7-ZipPortable\App\7-Zip\7z.exe"
set MakeNSIS="D:\Dropbox\SYNC\Program\win32paf\NSISPortable\App\NSIS\makensis.exe"


:: Compress=1 - Use CompressFiles
:: Compress=0 - Don't CompressFiles
set Compress=0


if not exist %PythonEXE%        call :FileNotFound %PythonEXE%
if not exist %SevenZipEXE%      call :FileNotFound %SevenZipEXE%
if not exist %MakeNSIS%         call :FileNotFound %MakeNSIS%


::Compile the Python-Script
%PythonEXE% setup.py py2exe
if not "%errorlevel%"=="0" (
        echo Py2EXE Error!
        pause
        goto:eof
)


:: Copy the Py2EXE Results to the SubDirectory and Clean Py2EXE-Results
rd "dist_EXE" /s /q
rd build /s /q
xcopy dist\*.* "dist_EXE\" /d /y
rd dist /s /q

::copy gmb.ico "dist_EXE\" /d /y
rem copy %PYTHONHOME%\Lib\site-packages\wx-2.8-msw-unicode\wx\msvcp71.dll "dist_EXE\" /d /y
rem copy %SystemRoot%\msvcp71.dll "dist_EXE\" /d /y

md dist_EXE\messages
md dist_EXE\messages\cs_CZ
md dist_EXE\messages\cs_CZ\LC_MESSAGES
md dist_EXE\messages\ru_RU
md dist_EXE\messages\ru_RU\LC_MESSAGES
md dist_EXE\messages\nl
md dist_EXE\messages\nl\LC_MESSAGES
md dist_EXE\messages\da
md dist_EXE\messages\da\LC_MESSAGES
copy gmail-backup.pot dist_EXE\messages
xcopy messages\cs_CZ\LC_MESSAGES\*.* "dist_EXE\messages\cs_CZ\LC_MESSAGES" /d /y
xcopy messages\ru_RU\LC_MESSAGES\*.* "dist_EXE\messages\ru_RU\LC_MESSAGES" /d /y
xcopy messages\nl\LC_MESSAGES\*.* "dist_EXE\messages\nl\LC_MESSAGES" /d /y
xcopy messages\da\LC_MESSAGES\*.* "dist_EXE\messages\da\LC_MESSAGES" /d /y

if "%Compress%"=="1" call:CompressFiles
echo.
echo.
echo Done: "dist_EXE\"
echo.

mkdir "inst_EXE"
%MakeNSIS% installer.nsi

echo Done: MakeNSIS

pause
goto:eof



:CompressFiles
        %SevenZipEXE% -aoa x "dist_EXE\library.zip" -o"dist_EXE\library\"
        del "dist_EXE\library.zip"

        cd dist_EXE\library\
        %SevenZipEXE% a -tzip -mx9 "..\library.zip" -r
        cd ..\..
        rd "dist_EXE\library" /s /q

        cd dist_EXE\
goto:eof



:FileNotFound
        echo.
        echo Error, File not found:
        echo [%1]
        echo.
        echo Check Path in %~nx0???
        echo.
        pause
        exit
goto:eof

