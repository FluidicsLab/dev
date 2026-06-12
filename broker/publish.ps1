
$publisher = "C:\\Program Files\\mosquitto\\mosquitto_pub.exe"

$url = "192.168.22.94:10088" 
$topic = "/hot/wifi/value"

if (Test-Path $publisher) {  

    $fname = "$PSScriptroot/data/payload.json"
    $h,$p = $url -split ":"        

    Write-Host $h $p $publisher

    $rcc = Start-Process $publisher -ArgumentList ("-h {0} -p {1} -t {2} -q 0 -V mqttv5 --quiet -f {3}" -f $h,$p,$topic,$fname) -PassThru -Wait -NoNewWindow        
    if ($rcc.ExitCode -ne 1) { 
        Write-Host ("ethercat response with {0} available - ok") -f $rcc.ExitCode
    } 
    else { 
        Write-Error ("ethercat response NOT {0} available - failure") -f $rcc.ExitCode
    }

} else {
    Write-Error "ethercat publisher not available - failure"
}