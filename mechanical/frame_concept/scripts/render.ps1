param([string]$OpenSCAD = 'openscad.com')
$ErrorActionPreference = 'Stop'
$modelRoot = Split-Path -Parent $PSScriptRoot
$outputRoot = Join-Path $modelRoot 'previews'
New-Item -ItemType Directory -Force -Path $outputRoot | Out-Null
$exe = (Get-Command $OpenSCAD -ErrorAction Stop).Source
$report = [System.Collections.Generic.List[string]]::new()
$report.Add('FRAME_CONCEPT_V1 — geometry validation; not structural/optical validation')
$report.Add('Defaults are assumptions. Sources: frame_concept.scad + included modules.')

function Invoke-Scad([string]$Arguments, [bool]$ExpectAssertion = $false) {
    $start = [System.Diagnostics.ProcessStartInfo]::new()
    $start.FileName = $exe
    $start.WorkingDirectory = $modelRoot
    $start.Arguments = $Arguments
    $start.UseShellExecute = $false
    $start.CreateNoWindow = $true
    $start.RedirectStandardError = $true
    $start.RedirectStandardOutput = $true
    $process = [System.Diagnostics.Process]::Start($start)
    $stderrTask = $process.StandardError.ReadToEndAsync()
    $stdoutTask = $process.StandardOutput.ReadToEndAsync()
    $process.WaitForExit()
    $log = $stdoutTask.Result + $stderrTask.Result
    # .echo redirects diagnostics into its output file, not stderr.
    if ($Arguments -match '-o\s+(?:"([^"]+\.echo)"|(\S+\.echo))') {
        $echoName = if ($Matches[1]) { $Matches[1] } else { $Matches[2] }
        $log += [System.IO.File]::ReadAllText((Join-Path $modelRoot $echoName))
    }
    $assertion = $log -match 'ERROR: Assertion'
    if ($ExpectAssertion) {
        if (-not $assertion) { throw "Expected range assertion missing: $Arguments" }
        $report.Add("PASS expected assertion: $Arguments")
    } else {
        if ($process.ExitCode -ne 0 -or $log -match 'ERROR:|WARNING:') { throw $log }
        $report.Add("PASS $Arguments")
    }
}

Invoke-Scad '--version'
foreach ($sceneName in @('color','measure','calibration')) {
    Invoke-Scad ('-D "scene=\"{0}\"" -o "previews/{0}.csg" frame_concept.scad' -f $sceneName)
}
foreach ($partName in @('camera_plate','board_tray','monitor_plate','light_bracket')) {
    Invoke-Scad ('-D "part=\"{0}\"" -o "previews/{0}.stl" frame_concept.scad' -f $partName)
}

$cameraArgs = '--imgsize=1600,1100 --camera=1200,-2400,2300,160,0,300 --projection=o --viewall --autocenter --colorscheme=Tomorrow'
foreach ($preset in @('color_open','measure_open','calibration_open','enclosed')) {
    Invoke-Scad (('-p presets.json -P {0} -D "show_fov=false" -o "previews/{0}.png" ' -f $preset) + $cameraArgs + ' frame_concept.scad')
}
Invoke-Scad '-D "scene=\"measure\"" -D "show_fov=false" -D "show_cables=false" -o previews/measure_top.png --imgsize=1400,1000 --camera=0,0,1600,0,0,0 --projection=o --viewall --autocenter --colorscheme=Tomorrow frame_concept.scad'
foreach ($sceneName in @('color','measure')) {
    Invoke-Scad ('-D "part=\"worktop\"" -D "scene=\"{0}\"" -o "previews/{0}_layout.png" --imgsize=1400,1000 --camera=0,0,800,0,0,0 --projection=o --viewall --autocenter --colorscheme=Tomorrow frame_concept.scad' -f $sceneName)
}
Invoke-Scad '-D "part=\"optics\"" -D "show_fov=false" -o previews/optics.png --imgsize=1400,1100 --camera=1000,-1500,700,0,0,300 --projection=o --viewall --autocenter --colorscheme=Tomorrow frame_concept.scad'
Invoke-Scad '-D "camera_h=350" -o previews/height_350.csg frame_concept.scad'
Invoke-Scad '-D "light_count=1" -o previews/one_light.csg frame_concept.scad'
Invoke-Scad '-D "camera_h=100" -o previews/invalid.echo frame_concept.scad' $true
$report.Add('Manual visual inspection required: open all PNGs, check attachment/clearance/layout.')
$report.Add('Manufacturing, loads, electrical integrity and measurement accuracy: NOT VERIFIED.')
[System.IO.File]::WriteAllLines((Join-Path $outputRoot 'validation.txt'),$report,[System.Text.UTF8Encoding]::new($false))
$report | ForEach-Object { Write-Output $_ }
