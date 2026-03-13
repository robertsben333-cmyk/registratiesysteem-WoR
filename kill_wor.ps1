$pids = (netstat -ano | Select-String "5050\s+LISTENING") | ForEach-Object { ($_ -split '\s+')[-1] } | Sort-Object -Unique
foreach ($p in $pids) {
    try {
        $proc = Get-Process -Id $p -ErrorAction SilentlyContinue
        if ($proc) { Write-Host "Killing PID $p ($($proc.ProcessName))"; $proc.Kill() }
        else {
            $wmi = Get-WmiObject Win32_Process -Filter "ProcessId=$p"
            if ($wmi) { Write-Host "WMI kill PID $p ($($wmi.Name))"; $wmi.Terminate() }
            else { Write-Host "PID $p not found in process list" }
        }
    } catch { Write-Host "Error on $p`: $_" }
}
Write-Host "Done"
