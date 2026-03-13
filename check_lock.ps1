$path = 'c:\Users\XavierFriesen\.projects SFNL\registratiesysteem WoR\dist\WoR Registratie.exe'
try {
    $fs = [System.IO.File]::Open($path, 'Open', 'Read', 'None')
    $fs.Close()
    Write-Host "NOT_LOCKED"
} catch {
    Write-Host "LOCKED: $($_.Exception.Message)"
}
