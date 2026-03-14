
$Host.UI.RawUI.BackgroundColor = "Black"
$Host.PrivateData.ProgressBackgroundColor = "DarkGreen"
$Host.PrivateData.ProgressForegroundColor = "Black"

Clear-Host

. "$PSScriptRoot\func.ps1"

$publisher = "C:\\Program Files\\mosquitto\\mosquitto_pub.exe"    

$url = "localhost:10097" 
$topic = "/hot/ecat/value"
$h,$p = $url -split ":"

$sleep = 50

$out = @()
$wrn = @()
$err = @()

[array]$CONTROL = @(
    '{ "source": "ed1fWorker", "target": 0, "value": { "control": { "mode": "p", "enabled": 1, "setpoint": 100.0, "processvalue": 100.0 } } }'
)

$setpoint = 4294967295 * 5.0
$setpoint = [int64]$setpoint

[array]$CONTROL = @(
    #"{ ""source"": ""ed1fWorker"", ""target"": 0, ""value"": { ""control"": { ""mode"": ""d"", ""target"": 0, ""enabled"": 1, ""setpoint"": $($setpoint), ""params"": [1000.0, 0.01, 0.001, 0.1] } } }"
    "{ ""source"": ""ed1fWorker"", ""target"": 0, ""value"": { ""control"": { ""mode"": ""d"", ""target"": 0, ""enabled"": 0, ""setpoint"": $($setpoint) } } }"
)

$payloads = $CONTROL

foreach ($payload in $payloads) 
{
    $fname = "$PSScriptroot\data\payload.json"
    $rcc = _publish $h $p $topic $payload $publisher $fname
    $out += ("send '{0}' by '{1}' with {2} - done" -f "", $payload, $rcc.ExitCode); _talk "I" $out[$out.Count - 1]        
    Start-Sleep -Milliseconds $sleep
}
