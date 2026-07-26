@echo off
chcp 65001 >nul
setlocal

rem Usage:
rem   sync_videos.bat [Windows source directory] [Linux destination directory]
rem Example:
rem   sync_videos.bat "D:\Videos" "/srv/media/videos"
rem
rem When omitted, the original directories are used.
set "WINDOWS_SOURCE=%~1"
set "LINUX_DEST=%~2"
if not defined WINDOWS_SOURCE set "WINDOWS_SOURCE=F:\"
if not defined LINUX_DEST set "LINUX_DEST=/srv/media/videos"

if not exist "%WINDOWS_SOURCE%\." (
    echo [ERROR] Windows source directory does not exist:
    echo         %WINDOWS_SOURCE%
    exit /b 2
)

if not "%LINUX_DEST:~0,1%"=="/" (
    echo [ERROR] Linux destination directory must be an absolute path:
    echo         %LINUX_DEST%
    exit /b 2
)

rem Convert a Windows path (for example D:\Videos) to its WSL path.
for /f "usebackq delims=" %%I in (`wsl -d Ubuntu wslpath -a "%WINDOWS_SOURCE%"`) do set "WSL_SOURCE=%%I"
if not defined WSL_SOURCE (
    echo [ERROR] Failed to convert the Windows source directory to a WSL path.
    exit /b 2
)

rem Remove trailing slashes, then add exactly one at the rsync call below.
if "%WSL_SOURCE:~-1%"=="/" set "WSL_SOURCE=%WSL_SOURCE:~0,-1%"
if not "%LINUX_DEST%"=="/" if "%LINUX_DEST:~-1%"=="/" set "LINUX_DEST=%LINUX_DEST:~0,-1%"

echo ============================================================
echo  %WINDOWS_SOURCE% (top-level folders)
echo    -^> minipc:%LINUX_DEST%
echo  Skip rule: same name + same size = already copied
echo ============================================================
echo.

rem -- Copy the Windows SSH key into WSL with mode 600 (idempotent).
rem    ssh inside WSL rejects keys on /mnt/c because they appear world-readable.
wsl -d Ubuntu bash -c "mkdir -p ~/.ssh && install -m 600 /mnt/c/Users/notoa/.ssh/id_ed25519 ~/.ssh/id_ed25519_win"
if errorlevel 1 (
    echo [ERROR] Failed to prepare SSH key inside WSL.
    pause
    exit /b 1
)

rem -- rsync via WSL.
rem    exclude rules       : Windows system folders ($RECYCLE.BIN etc.) are not media
rem    -f'+ /*/'            : include top-level directories
rem    -f'+ /*.[zZ][iI][pP]': also include top-level ZIP files
rem    -f'- /*'             : skip other loose files
rem    --size-only         : skip files that already exist with the same size
rem    --rsync-path        : minipc has no system rsync; use the user-space copy
wsl -d Ubuntu bash -c "rsync -av --size-only --chmod=D755,F644 --info=progress2,stats2 -f'- /$RECYCLE.BIN/' -f'- /System Volume Information/' -f'- /$WinREAgent/' -f'- /Recovery/' -f'+ /*/' -f'+ /*.[zZ][iI][pP]' -f'- /*' --rsync-path=/home/notoa/.local/rsync/usr/bin/rsync -e 'ssh -i ~/.ssh/id_ed25519_win -o StrictHostKeyChecking=accept-new' '%WSL_SOURCE%/' 'notoa@192.168.0.10:%LINUX_DEST%/'"
set RC=%ERRORLEVEL%

echo.
if %RC%==0 (
    echo Sync finished successfully.
) else (
    echo Sync ended with exit code %RC%. Check the output above.
)
pause
exit /b %RC%
