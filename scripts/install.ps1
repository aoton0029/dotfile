<#
  dotfiles installer (Windows / PowerShell)
  Creates symlinks from $HOME (and other targets) back into this repo.
  Requires: Developer Mode enabled, or run as Administrator (mklink requires elevation otherwise).
#>

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$Links = (Get-Content (Join-Path $RepoRoot "links.json") -Raw | ConvertFrom-Json).windows

function Resolve-Dest([string]$dest) {
    $expanded = $ExecutionContext.InvokeCommand.ExpandString($dest)
    if ($expanded.StartsWith("~")) {
        $expanded = Join-Path $HOME $expanded.Substring(1).TrimStart('\', '/')
    }
    return $expanded
}

foreach ($link in $Links) {
    $src  = Join-Path $RepoRoot $link.src
    $dest = Resolve-Dest $link.dest

    if (-not (Test-Path $src)) {
        Write-Warning "Skip (source missing): $src"
        continue
    }

    $destDir = Split-Path -Parent $dest
    if (-not (Test-Path $destDir)) {
        New-Item -ItemType Directory -Path $destDir -Force | Out-Null
    }

    if (Test-Path $dest) {
        $item = Get-Item $dest -Force
        if ($item.LinkType -eq "SymbolicLink") {
            Remove-Item $dest -Force
        } else {
            $backup = "$dest.backup"
            Write-Host "Backing up existing file: $dest -> $backup"
            Move-Item $dest $backup -Force
        }
    }

    New-Item -ItemType SymbolicLink -Path $dest -Target $src -Force | Out-Null
    Write-Host "Linked: $dest -> $src"
}

Write-Host "`nDone. Restart your shell / VSCode to pick up changes."
