import paramiko
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
try:
    client.connect('192.168.1.18', username='dungla', timeout=5)
    # Check if autonomous_training_loop is running
    stdin, stdout, stderr = client.exec_command('powershell -Command "Get-WmiObject Win32_Process | Where-Object { $_.CommandLine -match \'autonomous_training_loop\' } | Select-Object ProcessId, CommandLine"')
    out = stdout.read().decode('utf-8', errors='replace').strip()
    print("PROCESSES:")
    print(out if out else "None")
    
    # Check the logs of autonomous_training_loop if it was redirected
    # Or just check the most recent run log
    stdin, stdout, stderr = client.exec_command('powershell -Command "Get-ChildItem -Path d:\DungLA\Argo\workspaces\CFG_XAG_*_V*\runs\* -Directory | Sort-Object CreationTime -Descending | Select-Object -First 1 | ForEach-Object { Get-Content (Join-Path $_.FullName \'config.json\') -TotalCount 5; Get-Content (Join-Path $_.FullName \'prepare_dataset.log\') -Tail 10 -ErrorAction SilentlyContinue; Get-Content (Join-Path $_.FullName \'train_v*.log\') -Tail 10 -ErrorAction SilentlyContinue }"')
    out2 = stdout.read().decode('utf-8', errors='replace').strip()
    print("\nLATEST LOGS:")
    print(out2[:2000]) # Print first 2000 chars

except Exception as e:
    print(f"Error: {e}")
