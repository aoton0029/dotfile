# --- dotfiles: PowerShell profile ---

Set-PSReadLineOption -PredictionSource History
Set-PSReadLineOption -EditMode Windows

function ll { Get-ChildItem -Force @args }
function gs { git status @args }
function gco { git checkout @args }
function gp { git pull @args }

function .. { Set-Location .. }
function ... { Set-Location ..\.. }

$env:DOTFILES = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)

if (Get-Command starship -ErrorAction SilentlyContinue) {
    Invoke-Expression (&starship init powershell)
}
