
param(
    $uuid,
    $mandant,
    $duration,
    $prev
)

$cmd = "Scripts\python.exe" 
$venv = "C:\Environment\venv-hot\"

$fname = "report.$mandant.$duration.csv"

Write-Host $fname

$script = "C:\Develop\py\FluidicsLab\Drafts\report\template\report.$mandant.py $duration $fname"
$query = "$venv$cmd" 

Start-Process -Wait -NoNewWindow $query $script

if ($prev -eq 1) {
    Invoke-Item "C:\Data\store\reports\"
}