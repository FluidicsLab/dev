
function _progress {
    
    param(
        $value,
        $complete = $false
    )
    
    <#
    if ($complete) {
        Write-Progress -Id 0 -Completed
    } else {
        $step = 100 / 6
        $value *= $step
        Write-Progress -Id 0 -Activity "###" -Status " " -PercentComplete $value
    }
    Start-Sleep -Milliseconds 1000
    #>
}

function _window {
    param(
        $title
    )
$sig = @"
[DllImport("user32.dll", CharSet = CharSet.Auto)]
public static extern IntPtr FindWindow(string lpClassName, string lpWindowName);
"@
    $api = Add-Type -Name Funcs -Namespace Win32 -MemberDefinition $sig -PassThru
    $hwnd = $api::FindWindow([NullString]::Value, $title)
    if ($hwnd -ne [IntPtr]::Zero) { return $hwnd }
    else { return 0 }
}

function _bringtofront {
    param(
        $hwnd
    )

$sig = @"
[DllImport("user32.dll")] 
public static extern bool SetWindowPos(IntPtr hWnd, IntPtr hWndInsertAfter, int X,int Y, int cx, int cy, uint uFlags);
[DllImport("user32.dll")] 
public static extern bool ShowWindowAsync(IntPtr hWnd, int nCmdShow);
"@

    $api = Add-Type -Name Funcs2 -Namespace Win32 -MemberDefinition $sig -PassThru
    
    [Void]$api::SetWindowPos($hwnd, -1, 0, 0, 0, 0, 0x0002 + 0x0001 + 0x0040 )
    [Void]$api::ShowWindowAsync($hwnd, 4)
}

function _bringtofront2 {
    param (
        [Parameter()]
        [ValidateSet('FORCEMINIMIZE', 'HIDE', 'MAXIMIZE', 'MINIMIZE', 'RESTORE', 'SHOW', 'SHOWDEFAULT', 'SHOWMAXIMIZED', 'SHOWMINIMIZED', 'SHOWMINNOACTIVE', 'SHOWNA', 'SHOWNOACTIVATE', 'SHOWNORMAL')]
        $style = 'SHOW',    
        [Parameter()]
        $hwnd
    )

    $states = @{
        HIDE = 0
        SHOWNORMAL = 1
        SHOWMINIMIZED = 2
        SHOWMAXIMIZED = 3
        MAXIMIZE = 3
        SHOWNOACTIVATE = 4
        SHOW = 5
        MINIMIZE = 6
        SHOWMINNOACTIVE = 7
        SHOWNA = 8
        RESTORE = 9
        SHOWDEFAULT = 10
        FORCEMINIMIZE = 11
    }

$Win32ShowWindowAsync = Add-Type -Name "Win32ShowWindowAsync" -Namespace Win32Functions -PassThru -MemberDefinition @"
[DllImport("user32.dll")] 
public static extern bool ShowWindowAsync(IntPtr hWnd, int nCmdShow);
"@

    $Win32ShowWindowAsync::ShowWindowAsync($hwnd, $states[$style]) | Out-Null
}

function _bringtofrontByTitle {
    param (
        [Parameter()]
        $title
    )
    $hwnd = _window -title $title
    return _bringtofront -hwnd $hwnd
}

function _closeWindow {
    param (
        [Parameter()]
        $hwnd
    )

$Win32CloseWindow = Add-Type -Name "Win32CloseWindow" -Namespace "Win32Functions" -PassThru -MemberDefinition @"
[DllImport("user32.dll")] 
public static extern bool CloseWindow(IntPtr hWnd);
[DllImport("user32.dll")] 
public static extern bool DestroyWindow(IntPtr hWnd);
[DllImport("user32.dll")]
public static extern bool IsWindowVisible(IntPtr hWnd);
[DllImport("user32.dll", CharSet = CharSet.Auto, SetLastError = true)]
public static extern IntPtr SendMessage(IntPtr hWnd, uint msg, int wParam, string lParam);
"@  
    if ($Win32CloseWindow::IsWindowVisible($hwnd) -eq $true) {
        return $Win32CloseWindow::SendMessage($hwnd, 0x010, 0, "")
    }
    return 0
}

function _closeWindowByTitle {
    param (
        [Parameter()]
        $title
    )
    $hwnd = _window -title $title
    return _closeWindow -hwnd $hwnd
}

function _yn {
    param (
        [string]$message = "    Continue proceeding?"
    )

    #return $true

    while ($true) {        
        Write-Host "    $message" -ForegroundColor DarkRed -NoNewline
        $resp = Read-Host " (Y/N)"
        $resp = $resp.Trim().ToLower()
        switch ($resp) {
            'y' { return $true }
            'n' { return $false }
            default {
                Write-Host "    'Y' or 'N' allowed only" -ForegroundColor DarkYellow
            }
        }
    }
}

function _app {
    param ([string]$name)    
    $apps = (New-Object -ComObject Shell.Application).NameSpace('shell:::{4234d49b-0245-4df3-b780-3893943456e1}').Items()    
    if ($name) {
        $rc = $apps | Where-Object { $_.name -like "*$name*" } | Select-Object name,@{n="AUMID";e={$_.path}}
        if ($rc) { return 0, $rc }
        else { return -1, "unable to locate {0}" -f $name }
    }    
    return -2, "name not given - failure"
}

function _verbose {
    param(
        $name, $out, $wrn, $err
    )
    Write-Host "    $name" -ForegroundColor DarkCyan

    if ($out.Count -ne 0) {
        Write-Host ("--- {0} information" -f $out.Count) -ForegroundColor Gray
        foreach ($o in $out) { Write-Host ("    {0}" -f $o) }
    }

    if ($wrn.Count -ne 0) {
        Write-Host ("--- {0} warning" -f $wrn.Count) -ForegroundColor DarkYellow
        foreach ($w in $wrn) { Write-Host ("    {0}" -f $w) }
    }

    if ($err.Count -ne 0) {
        Write-Host ("--- {0} error" -f $err.Count) -ForegroundColor DarkRed
        foreach ($e in $err) { Write-Host ("    {0}" -f $e) }            
    }
}

function _talk {
    param(
        $mode, $msg
    )
    switch ($mode) {
        "W" {       Write-Host ("    {0} {1}" -f $mode,$msg) -ForegroundColor DarkYellow }
        "E" {       Write-Host ("    {0} {1}" -f $mode,$msg) -ForegroundColor DarkRed }
        default {   Write-Host ("    {0} {1}" -f $mode,$msg) -ForegroundColor Gray }
    }
    
}

function _convert_to_hash {    
    [OutputType([System.Collections.Hashtable])]
    [CmdletBinding(SupportsShouldProcess = $False)]
    param (
        [Parameter(Position = 0, ValueFromPipeline)]
        $InputObject
    )

    process {
        if ($null -eq $InputObject) {
            return $null
        }

        if ($InputObject -is [System.Collections.IEnumerable] -and $InputObject -isnot [System.String]) {
            $collection = @(foreach ($object in $InputObject) { _convert_to_hash -InputObject $object })
            Write-Output -NoEnumerate -InputObject $collection
        }
        elseif ($InputObject -is [PSObject]) {
            $hash = @{ }
            foreach ($property in $InputObject.PSObject.Properties) { $hash[$property.Name] = _convert_to_hash -InputObject $property.Value }
            Write-Output -InputObject $hash
        }
        else {
            Write-Output -InputObject $InputObject
        }
    }
}

function _publish {
    param(
        $_host,
        $_port,
        $_topic,
        $_payload,
        $_publisher,
        $_fname
    )

    $_payload | Set-Content -Path $_fname -Encoding ascii            
    $rcc = Start-Process $_publisher -ArgumentList ("-h {0} -p {1} -t {2} -q 0 -V mqttv5 --quiet -f {3}" -f $_host,$_port,$_topic,$fname) -PassThru -Wait -NoNewWindow
    return $rcc
}