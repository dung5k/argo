param([string]$ip, [string]$user, [string]$pass)

Write-Output "Downloading plink..."
Invoke-WebRequest -Uri "https://the.earth.li/~sgtatham/putty/latest/w64/plink.exe" -OutFile "plink.exe"
$plink = ".\plink.exe"

$pubKey = Get-Content ~/.ssh/id_rsa.pub
$encodedKey = [Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes($pubKey))

$scriptBlock = "mkdir -p ~/.ssh && echo $encodedKey | base64 -d >> ~/.ssh/authorized_keys && chmod 700 ~/.ssh && chmod 600 ~/.ssh/authorized_keys"

$startInfo = New-Object System.Diagnostics.ProcessStartInfo
$startInfo.FileName = $plink
$startInfo.Arguments = "-ssh $user@$ip -pw $pass -batch `"$scriptBlock`""
$startInfo.UseShellExecute = $false
$startInfo.RedirectStandardInput = $true
$startInfo.RedirectStandardOutput = $true
$startInfo.RedirectStandardError = $true

$process = New-Object System.Diagnostics.Process
$process.StartInfo = $startInfo
$process.Start() | Out-Null

Start-Sleep -Seconds 2
if (!$process.HasExited) {
    $process.StandardInput.WriteLine("y")
}
Start-Sleep -Seconds 5

if ($process.HasExited) {
    Write-Output "Exit code: $($process.ExitCode)"
    Write-Output "Stdout: $($process.StandardOutput.ReadToEnd())"
    Write-Output "Stderr: $($process.StandardError.ReadToEnd())"
} else {
    Write-Output "Process is still running. Killing it."
    $process.Kill()
}
