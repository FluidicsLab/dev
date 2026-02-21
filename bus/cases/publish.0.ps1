
$Host.UI.RawUI.BackgroundColor = "Black"
$Host.PrivateData.ProgressBackgroundColor = "DarkGreen"
$Host.PrivateData.ProgressForegroundColor = "Black"

Clear-Host

. "$PSScriptRoot\func.ps1"

$publisher = "C:\\Program Files\\mosquitto\\mosquitto_pub.exe"    

$url = "localhost:10097" 
$topic = "/hot/ecat/value"
$h,$p = $url -split ":"

$sleep = 10

$out = @()
$wrn = @()
$err = @()

function mulmin2incs {
    param(
        $value
    )

    $gearBoxGearRatio = 1000.
    $spindlePitch = 5.
    $timingBeltTransmissionGearRatio = 2.
    $motorIncrementPositions = 8388608
    $cylinderDiameter = 15.
    $cylinderVolume = 10.
   
    $cylinderArea = [math]::Pow($cylinderDiameter,2.) * [math]::PI / 4.
    $transmission = $spindlePitch / ($timingBeltTransmissionGearRatio * $gearBoxGearRatio)
    $injectionRateRotation = $transmission * $cylinderArea
    $injectionRateIncrement = $injectionRateRotation / $motorIncrementPositions
    return [int]($value / ($injectionRateIncrement * 60))
}

# control word 

# 9 pp change on setpoint
# 8 halt
# 7 fault reset
# 6 pp absolute / relative
# 5 pp change set immediately
# 4 pp new setpoint
# 3 enable operation
# 2 quick stop
# 1 enable voltage
# 0 switch on

$speed = mulmin2incs(100)
$speed = $speed.ToString()

Write-Host $speed

[array]$OFF = @(
    "{ ""source"": ""ed1fWorker"", ""target"": 0, ""value"": { ""control"": ""0000000000000111"" } }",
    '{ "source": "ed1fWorker", "target": 0, "value": { "control": "0000000000000101" } }',
    '{ "source": "ed1fWorker", "target": 0, "value": { "control": "0000000000000100" } }'
)

[array]$SP = @(
    '{ "source": "ed1fWorker", "target": 0, "value": { "control": "0000000000000100" } }',
    '{ "source": "ed1fWorker", "target": 0, "value": { "control": "0000000000000110" } }',
    "{ ""source"": ""ed1fWorker"", ""target"": 0, ""value"": { ""control"": ""0000000000000111"", ""velocity"": $($speed) } }",
    '{ "source": "ed1fWorker", "target": 0, "value": { "control": "0000000000001111" } }'
)

[array]$ON = @(
    '{ "source": "ed1fWorker", "target": 0, "value": { "control": "0000000000001111" } }'
)

$payloads = $OFF

foreach ($payload in $payloads) 
{
    $fname = "$PSScriptroot\data\payload.json"
    $rcc = _publish $h $p $topic $payload $publisher $fname
    $out += ("send '{0}' by '{1}' with {2} - done" -f "", $payload, $rcc.ExitCode); _talk "I" $out[$out.Count - 1]        
    Start-Sleep -Milliseconds $sleep
}

# _verbose -name "SETUP" -out $out -wrn $wrn -err $err 