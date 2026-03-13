Get-ChildItem "$env:TEMP" -Directory -Filter "_MEI*" | Sort-Object LastWriteTime | ForEach-Object {
    $hasDash = Test-Path (Join-Path $_.FullName "app\templates\base.html")
    $dashFound = $false
    if ($hasDash) {
        $dashFound = (Get-Content (Join-Path $_.FullName "app\templates\base.html") | Select-String "dashboard" -CaseSensitive) -ne $null
    }
    Write-Host "$($_.LastWriteTime)  $($_.Name)  Dashboard=$dashFound"
}
