powershell -Command "Get-WmiObject Win32_Process | Where-Object { $_.CommandLine -match 'python' } | Select-Object ProcessId, CommandLine"
