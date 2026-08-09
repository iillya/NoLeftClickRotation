@echo off
cd /d "%~dp0"
call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat" >nul
cl /nologo /O2 /W3 /LD /utf-8 /DUNICODE /D_UNICODE /Fe:NoLeftClickRotation.dll NoLeftClickRotation.c /link user32.lib comctl32.lib gdi32.lib
if errorlevel 1 exit /b 1
echo BUILD_OK
