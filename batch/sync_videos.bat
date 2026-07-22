@echo off
chcp 65001 >nul
setlocal

echo ============================================================
echo  F:\ (top-level folders) -^> minipc:/srv/media/videos
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
rem    -f'+ /*/' -f'- /*'  : top-level directories only, skip loose files in F:\
rem    --size-only         : skip files that already exist with the same size
rem    --rsync-path        : minipc has no system rsync; use the user-space copy
wsl -d Ubuntu bash -c "rsync -av --size-only --chmod=D755,F644 --info=progress2,stats2 -f'- /$RECYCLE.BIN/' -f'- /System Volume Information/' -f'- /$WinREAgent/' -f'- /Recovery/' -f'+ /*/' -f'- /*' --rsync-path=/home/notoa/.local/rsync/usr/bin/rsync -e 'ssh -i ~/.ssh/id_ed25519_win -o StrictHostKeyChecking=accept-new' /mnt/f/ notoa@192.168.0.10:/srv/media/videos/"
set RC=%ERRORLEVEL%

echo.
if %RC%==0 (
    echo Sync finished successfully.
) else (
    echo Sync ended with exit code %RC%. Check the output above.
)
pause
exit /b %RC%
