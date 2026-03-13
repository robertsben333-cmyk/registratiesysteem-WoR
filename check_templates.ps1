$meiDirs = Get-ChildItem "$env:TEMP" -Directory -Filter "_MEI*" -ErrorAction SilentlyContinue
if (-not $meiDirs) { Write-Host "No _MEI dirs found in $env:TEMP" }
foreach ($d in $meiDirs) {
    Write-Host "Checking: $($d.FullName)"
    $base = Join-Path $d.FullName "app\templates\base.html"
    if (Test-Path $base) {
        $content = Get-Content $base
        $dashLine = $content | Select-String "dashboard" -CaseSensitive
        if ($dashLine) { Write-Host "  DASHBOARD FOUND: $dashLine" }
        else { Write-Host "  NO DASHBOARD LINK in base.html" }
    } else {
        Write-Host "  base.html not found at $base"
    }
}
