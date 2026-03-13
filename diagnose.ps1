Write-Host "=== Port 5050 ==="
$lines = netstat -ano | Select-String "5050\s+LISTEN"
foreach ($l in $lines) { Write-Host $l }

Write-Host "`n=== Processes ==="
$pids = $lines | ForEach-Object { ($_ -split '\s+')[-1] } | Sort-Object -Unique
foreach ($p in $pids) {
    $proc = Get-Process -Id $p -ErrorAction SilentlyContinue
    $wmi = Get-WmiObject Win32_Process -Filter "ProcessId=$p" -ErrorAction SilentlyContinue
    if ($proc) { Write-Host "PID $p - $($proc.ProcessName) - $($proc.Path)" }
    elseif ($wmi) { Write-Host "PID $p (WMI) - $($wmi.Name) - $($wmi.ExecutablePath)" }
    else { Write-Host "PID $p - NOT FOUND in process list" }
}

Write-Host "`n=== _MEI dirs (newest first) ==="
Get-ChildItem "$env:TEMP" -Directory -Filter "_MEI*" | Sort-Object LastWriteTime -Descending | Select-Object -First 5 | ForEach-Object {
    $hasDash = (Get-ChildItem (Join-Path $_.FullName "app\templates\base.html") -ErrorAction SilentlyContinue) -ne $null
    if ($hasDash) {
        $dashFound = (Get-Content (Join-Path $_.FullName "app\templates\base.html") | Select-String "dashboard" -CaseSensitive) -ne $null
        Write-Host "$($_.LastWriteTime)  $($_.Name)  Dashboard=$dashFound"
    } else {
        Write-Host "$($_.LastWriteTime)  $($_.Name)  (no base.html)"
    }
}
