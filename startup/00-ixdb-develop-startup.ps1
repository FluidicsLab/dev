

$cmd = "C:\Tools\influxdb2-2.7.10-windows\influxd.exe"
$param = "--http-idle-timeout=0 --http-read-header-timeout=0"

$prefix = 'graph'

Start-Process wt -ArgumentList "-w hot -p hot-nred --title $prefix $cmd $param"

