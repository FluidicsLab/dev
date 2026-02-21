
param(
    $uuid,
    $mandant,
    $measurement,
    $duration,
    $prev
)

$cmd = "Scripts\python.exe" 
$venv = "C:\Environment\venv-hot\"

$fname = "report.$mandant.$measurement.$duration.csv"

$script = "C:\Develop\py\FluidicsLab\Drafts\report\template\report.$mandant.py $measurement $duration $fname"
$query = "$venv$cmd" 

Start-Process -Wait -NoNewWindow $query $script

if ($prev -eq 1) {
    Invoke-Item "C:\Data\store\reports\"
}