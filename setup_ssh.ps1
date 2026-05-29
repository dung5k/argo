param([string]$ip, [string]$user, [string]$pass)
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName Microsoft.VisualBasic
$pubKey = Get-Content ~/.ssh/id_rsa.pub
$cmd = "mkdir -p ~/.ssh && echo '$pubKey' >> ~/.ssh/authorized_keys && chmod 700 ~/.ssh && chmod 600 ~/.ssh/authorized_keys"
$startInfo = New-Object System.Diagnostics.ProcessStartInfo
$startInfo.FileName = "ssh"
$startInfo.Arguments = "$user@$ip `"$cmd`""
$startInfo.UseShellExecute = $false
$startInfo.RedirectStandardInput = $true
$startInfo.RedirectStandardOutput = $true
$startInfo.RedirectStandardError = $true
$process = New-Object System.Diagnostics.Process
$process.StartInfo = $startInfo
$process.Start() | Out-Null
Start-Sleep -Seconds 2
$process.StandardInput.WriteLine("yes")
Start-Sleep -Seconds 1
$process.StandardInput.WriteLine($pass)
Start-Sleep -Seconds 5
if ($process.HasExited) {
    Write-Output "Exit code: $($process.ExitCode)"
    Write-Output "Stdout: $($process.StandardOutput.ReadToEnd())"
    Write-Output "Stderr: $($process.StandardError.ReadToEnd())"
} else {
    Write-Output "Process is still running. Killing it."
    $process.Kill()
}
