
$user = "norman"
$location = "C:\Users\$user\.node-red"

$cmd = "node.exe" 
$a = "C:\Users\$user\AppData\Roaming\npm\node_modules\node-red\red.js"

Set-Location $location
$location = Get-Location 

$item = 'develop'
$title = "develop"

$folder = "$location\$item"
$f = "$folder\flows.json"
$arg = "$a --userDir $folder --settings $folder\settings.js --title $title $f"

Write-Host "--- $item startup $folder"

$query = "$cmd $arg"
Start-Process wt -ArgumentList "-w hot -p hot-nred --title $title $query"
