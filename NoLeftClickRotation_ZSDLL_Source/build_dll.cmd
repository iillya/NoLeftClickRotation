@echo off
setlocal
call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 (
  echo [ERROR] vcvars64.bat not found. Install VS2022 Build Tools with the C++ workload.
  exit /b 1
)
cl /nologo /utf-8 /O2 /MT /LD /W3 NoLeftClickRotation.c /Fe:NoLeftClickRotation.dll /link user32.lib comctl32.lib
if errorlevel 1 exit /b 1
echo.
echo Build OK: NoLeftClickRotation.dll
