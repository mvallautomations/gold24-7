$conn = Get-NetTCPConnection -LocalPort 8082 -State Listen -ErrorAction SilentlyContinue
if ($null -ne $conn) {
    Stop-Process -Id $conn.OwningProcess -Force -ErrorAction SilentlyContinue
    Write-Host "Killed previous bridge process"
}
Start-Sleep -Seconds 1
Start-Process "C:\Users\Legion\AppData\Local\Programs\Python\Python313\python.exe" -ArgumentList "C:\Users\Legion\mt5_bridge\mt5_bridge_server.py" -WindowStyle Hidden
Start-Sleep -Seconds 3
$newConn = Get-NetTCPConnection -LocalPort 8082 -State Listen -ErrorAction SilentlyContinue
if ($null -ne $newConn) {
    Write-Host "MT5 Bridge successfully listening on port 8082 (PID: $($newConn.OwningProcess))"
} else {
    Write-Host "Warning: MT5 Bridge did not report listening on port 8082 yet"
}
