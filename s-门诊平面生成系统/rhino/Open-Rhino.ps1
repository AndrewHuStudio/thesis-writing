$ErrorActionPreference = 'Stop'
$system = (Get-ItemProperty -LiteralPath 'HKLM:\SOFTWARE\McNeel\Rhinoceros\9.0\Install').Path
$rhino = Get-Item -LiteralPath (Join-Path $system 'Rhino.exe')
$plugin = Get-Item -LiteralPath (Join-Path $PSScriptRoot 'bin/Chat-0.3.40/OutpatientRhino.rhp')
$loader = Get-Item -LiteralPath (Join-Path $PSScriptRoot 'LoadInRhino.py')
# Rhino can restore a docked panel before the startup macro runs.
$key = 'HKCU:\Software\McNeel\Rhinoceros\9.0\Plug-Ins\0156ac98-6880-4a24-8584-d461fa55fb78'
$registration = Join-Path $key 'PlugIn'
if (Test-Path -LiteralPath $registration) {
    Set-ItemProperty -LiteralPath $registration -Name FileName -Value $plugin.FullName
    Set-ItemProperty -LiteralPath $key -Name RuiFile -Value ([IO.Path]::ChangeExtension($plugin.FullName, '.rui'))
}
$previous = $env:OUTPATIENT_RHP_TO_LOAD
try {
    $env:OUTPATIENT_RHP_TO_LOAD = $plugin.FullName
    $macro = '/runscript="-_RunPythonScript (' + $loader.FullName + ')"'
    Start-Process -FilePath $rhino.FullName -ArgumentList '/nosplash','/notemplate',$macro -WindowStyle Normal
} finally {
    $env:OUTPATIENT_RHP_TO_LOAD = $previous
}
