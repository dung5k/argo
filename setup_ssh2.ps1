param([string]$ip, [string]$user, [string]$pass)
$pubKey = Get-Content ~/.ssh/id_rsa.pub
$encodedKey = [Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes($pubKey))
$plinkArgs = "-ssh $user@$ip -pw $pass -batch `"echo $encodedKey | base64 -d >> ~/.ssh/authorized_keys && chmod 700 ~/.ssh && chmod 600 ~/.ssh/authorized_keys`""
Write-Output "Make sure you have plink.exe in your PATH, or we will try to download it."
if (!(Get-Command plink.exe -ErrorAction SilentlyContinue)) {
    Write-Output "Downloading plink..."
    Invoke-WebRequest -Uri "https://the.earth.li/~sgtatham/putty/latest/w64/plink.exe" -OutFile "plink.exe"
    $plink = ".\plink.exe"
} else {
    $plink = "plink.exe"
}
& $plink -ssh $user@$ip -pw $pass -batch "mkdir -p ~/.ssh && echo $encodedKey | base64 -d >> ~/.ssh/authorized_keys && chmod 700 ~/.ssh && chmod 600 ~/.ssh/authorized_keys"
