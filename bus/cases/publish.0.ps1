
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

function set-IRI {

    $electronicGearRatio = 1.0/1.0

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

    Set-Variable -Name "IRI" -Value ($injectionRateIncrement * 60) -Scope Global

    Write-Host $IRI
}

function mulmin2incs {
    param($value)    
    return [int]($value / $IRI)
}

function incs2mulmin {
    param($value)
    return [int]($value * $IRI)
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

set-IRI
$speed = mulmin2incs(200)
$velo = incs2mulmin($speed)

$speed = $speed.ToString()

Write-Host $speed " " $velo

[array]$RUN = @(
    '{ "source": "ed1fWorker", "target": 0, "value": { "command": "10000000" } }',
    '{ "source": "ed1fWorker", "target": 0, "value": { "command": "00000110" } }',
    '{ "source": "ed1fWorker", "target": 0, "value": { "command": "00000111" } }'
    "{ ""source"": ""ed1fWorker"", ""target"": 0, ""value"": { ""velocity"": $($speed) } }",
    '{ "source": "ed1fWorker", "target": 0, "value": { "command": "00001111" } }'
)

[array]$ENABLE = @(
    '{ "source": "ed1fWorker", "target": 0, "value": { "command": "10000000" } }',
    '{ "source": "ed1fWorker", "target": 0, "value": { "command": "00000110" } }',
    '{ "source": "ed1fWorker", "target": 0, "value": { "command": "00000111" } }',
    '{ "source": "ed1fWorker", "target": 0, "value": { "command": "00001111" } }'
)

[array]$DISABLE = @(
    '{ "source": "ed1fWorker", "target": 0, "value": { "command": "00000111" } }',
    '{ "source": "ed1fWorker", "target": 0, "value": { "command": "00000110" } }',
    '{ "source": "ed1fWorker", "target": 0, "value": { "command": "00000000" } }',
    '{ "source": "ed1fWorker", "target": 0, "value": { "command": "00000010" } }'
)

$payloads = $DISABLE
$payloads = $ENABLE
#$payloads = $RUN
#$payloads = @()

foreach ($payload in $payloads) 
{
    $fname = "$PSScriptroot\data\payload.json"
    $rcc = _publish $h $p $topic $payload $publisher $fname
    $out += ("send '{0}' by '{1}' with {2} - done" -f "", $payload, $rcc.ExitCode); _talk "I" $out[$out.Count - 1]        
    Start-Sleep -Milliseconds $sleep
}

# _verbose -name "SETUP" -out $out -wrn $wrn -err $err 