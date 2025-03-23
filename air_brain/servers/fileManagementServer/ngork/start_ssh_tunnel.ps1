# Check if ngrok is in PATH
if (-not (Get-Command ngrok -ErrorAction SilentlyContinue)) {
    Write-Host "[!] Ngrok is not installed or not in PATH."
    Write-Host "→ Download it from: https://ngrok.com/download"
    exit
}

# Check if SSH server is running
$sshStatus = Get-Service -Name sshd -ErrorAction SilentlyContinue
if ($sshStatus -eq $null -or $sshStatus.Status -ne "Running") {
    Write-Host "[!] OpenSSH Server is not running. Please enable it:"
    Write-Host "1. Go to Settings → Apps → Optional Features"
    Write-Host "2. Install 'OpenSSH Server' if not installed"
    Write-Host "3. Then run: Start-Service sshd"
    exit
}

# Kill existing ngrok sessions
Get-Process ngrok -ErrorAction SilentlyContinue | Stop-Process -Force

# Start ngrok TCP tunnel on port 22
Write-Host "[+] Starting Ngrok TCP tunnel on port 22..."
Start-Process -NoNewWindow -FilePath "ngrok" -ArgumentList "tcp 22"
Start-Sleep -Seconds 5

# Get Ngrok tunnel info
try {
    $apiResponse = Invoke-RestMethod -Uri "http://127.0.0.1:4040/api/tunnels"
    $tcpTunnel = $apiResponse.tunnels | Where-Object { $_.proto -eq "tcp" }

    if ($tcpTunnel.public_url) {
        $publicUrl = $tcpTunnel.public_url
        $hostPort = $publicUrl -replace "tcp://", ""
        $parts = $hostPort -split ":"
        $host = $parts[0]
        $port = $parts[1]
        $username = $env:USERNAME

        Write-Host ""
        Write-Host "[🔐] Use this SSH command from another computer:`n"
        Write-Host "ssh $username@$host -p $port`n"
        Write-Host "[✅] Username auto-filled as: $username"
    } else {
        Write-Host "[!] Could not retrieve Ngrok tunnel. Is it running?"
    }
} catch {
    Write-Host "[!] Failed to contact Ngrok API. Is Ngrok running?"
}
