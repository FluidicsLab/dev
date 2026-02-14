
$dev = "C:\Develop\py\fluidxlab\dev\bus\util\"
$item = 'drive.broker.py'

$cmd = "Scripts\python.exe" 
$venv = "C:\Environment\venv-hot\"

$title = 'broker'

$query = "$venv$cmd $dev$item"
Start-Process wt -ArgumentList "-w hot -p hot-nred --title $title $query"
