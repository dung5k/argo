$processes = Get-CimInstance Win32_Process -Filter "Name = 'python.exe'"
foreach ($p in $processes) {
    if ($p.CommandLine -match "bot_v6.py") {
        Write-Host "Killing Process ID: $($p.ProcessId)"
        Stop-Process -Id $p.ProcessId -Force
    }
}
