
$Host.UI.RawUI.BackgroundColor = "Black"
$Host.PrivateData.ProgressBackgroundColor = "DarkGreen"
$Host.PrivateData.ProgressForegroundColor = "Black"

Clear-Host

. "$PSScriptRoot\func.ps1"

$publisher = "C:\\Program Files\\mosquitto\\mosquitto_pub.exe"    

$url = "localhost:10097" 
$topic = "/hot/ecat/value"
$h,$p = $url -split ":"

$sleep = 200

$out = @()
$wrn = @()
$err = @()

[array]$MEM = @(
    #'{ "source": "el6080", "target": 2, "value": { "data": [0, 0, 0] } }'
    '{ "source": "el6080", "target": 2, "value": { "multiturn": 0 } }'
)

$payloads = $MEM

foreach ($payload in $payloads) 
{
    $fname = "$PSScriptroot\data\payload.json"
    $rcc = _publish $h $p $topic $payload $publisher $fname
    $out += ("send '{0}' by '{1}' with {2} - done" -f "", $payload, $rcc.ExitCode); _talk "I" $out[$out.Count - 1]        
    Start-Sleep -Milliseconds $sleep
}
