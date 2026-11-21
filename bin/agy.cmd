@echo off
setlocal EnableExtensions
rem Wrapper inteligente para agy en Windows: inicia siempre con --dangerously-skip-permissions por defecto.

if /i "%~1"=="update" goto :do_update
if /i "%~1"=="upgrade" goto :do_update

rem Resolver REAL_HOME dinamicamente (inmune a perfiles aislados %USERPROFILE%\.agyc_homes\<alias>)
set "REAL_HOME=%AGYC_REAL_HOME%"
if not defined REAL_HOME set "REAL_HOME=%USERPROFILE%"
set "TEST_CUT=%REAL_HOME:\.agyc_homes\=%"
if /i not "%TEST_CUT%"=="%REAL_HOME%" goto :strip_real_home
set "TEST_CUT=%REAL_HOME:/.agyc_homes/=%"
if /i not "%TEST_CUT%"=="%REAL_HOME%" goto :strip_real_home
goto :done_real_home
:strip_real_home
for /f "delims=" %%R in ('python -c "import sys; s=sys.argv[1].replace('\\','/'); i=s.find('/.agyc_homes'); print(sys.argv[1][:i] if i!=-1 else sys.argv[1])" "%REAL_HOME%" 2^>nul') do set "REAL_HOME=%%R"
:done_real_home

rem Buscar unicamente binarios nativos reales (jamas este wrapper .cmd para evitar recursion)
set "REAL_AGY="
if defined REAL_HOME if exist "%REAL_HOME%\.gemini\antigravity-cli\bin\agy-real.exe" set "REAL_AGY=%REAL_HOME%\.gemini\antigravity-cli\bin\agy-real.exe"
if not defined REAL_AGY if exist "%USERPROFILE%\.gemini\antigravity-cli\bin\agy-real.exe" set "REAL_AGY=%USERPROFILE%\.gemini\antigravity-cli\bin\agy-real.exe"
if not defined REAL_AGY if exist "%LOCALAPPDATA%\agyc\bin\agy-real.exe" set "REAL_AGY=%LOCALAPPDATA%\agyc\bin\agy-real.exe"
if not defined REAL_AGY if exist "%LOCALAPPDATA%\agy\bin\agy-real.exe" set "REAL_AGY=%LOCALAPPDATA%\agy\bin\agy-real.exe"
if not defined REAL_AGY if exist "%LOCALAPPDATA%\agy\bin\agy.exe" set "REAL_AGY=%LOCALAPPDATA%\agy\bin\agy.exe"

if not defined REAL_AGY (
  for /f "delims=" %%P in ('where agy-real.exe 2^>nul') do (
    if not defined REAL_AGY if /i "%%~xP"==".exe" if /i not "%%~dpP"=="%~dp0" set "REAL_AGY=%%~fP"
  )
)
if not defined REAL_AGY (
  for /f "delims=" %%P in ('where agy.exe 2^>nul') do (
    if not defined REAL_AGY if /i "%%~xP"==".exe" if /i not "%%~dpP"=="%~dp0" if /i not "%%~dpP"=="%LOCALAPPDATA%\agyc\bin\" set "REAL_AGY=%%~fP"
  )
)

if not defined REAL_AGY (
  echo Error: No se encontro el motor nativo de Google Antigravity ^('agy-real.exe' o 'agy.exe'^). 1>&2
  echo Rutas verificadas: 1>&2
  echo   - %REAL_HOME%\.gemini\antigravity-cli\bin\agy-real.exe 1>&2
  echo   - %LOCALAPPDATA%\agy\bin\agy.exe 1>&2
  echo Ejecuta 'agyc update' para descargar e instalar el binario oficial. 1>&2
  exit /b 1
)

rem Verificar si el usuario ya especifico --dangerously-skip-permissions
set "HAS_FLAG=0"
:check_args
if "%~1"=="" goto :run_agy
if "%~1"=="--dangerously-skip-permissions" set "HAS_FLAG=1"
shift
goto :check_args

:run_agy
rem Forzar almacenamiento basado en archivo (evita que agy.exe lea la credencial global de Windows Credential Manager)
if not defined SSH_TTY if not defined SSH_CLIENT set "SSH_TTY=/dev/pts/0"
if "%HAS_FLAG%"=="0" (
  "%REAL_AGY%" --dangerously-skip-permissions %*
) else (
  "%REAL_AGY%" %*
)
exit /b %ERRORLEVEL%

:do_update
shift
set "UPD_ARGS="
:collect_upd
if "%~1"=="" goto :run_update
set "UPD_ARGS=%UPD_ARGS% %1"
shift
goto :collect_upd

:run_update
if exist "%~dp0agyc.cmd" (
  call "%~dp0agyc.cmd" update%UPD_ARGS%
) else (
  python "%~dp0agyc" update%UPD_ARGS%
)
exit /b %ERRORLEVEL%
