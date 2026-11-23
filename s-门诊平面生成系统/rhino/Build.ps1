param([string]$RhinoSystemDir, [string]$Dotnet, [string]$OutputDirectory = (Join-Path $PSScriptRoot 'bin/Chat-0.3.40'))

$ErrorActionPreference = 'Stop'
if (-not $RhinoSystemDir) {
    $RhinoSystemDir = (Get-ItemProperty -LiteralPath 'HKLM:\SOFTWARE\McNeel\Rhinoceros\9.0\Install').Path
}
if (-not $Dotnet) {
    $userDotnet = Join-Path $env:LOCALAPPDATA 'Microsoft/dotnet/dotnet.exe'
    $Dotnet = if (Test-Path -LiteralPath $userDotnet -PathType Leaf) { $userDotnet } else { 'dotnet' }
}
$project = Join-Path $PSScriptRoot 'OutpatientRhino.csproj'
& $Dotnet build $project -c Release --nologo --output $OutputDirectory "-p:RhinoSystemDir=$($RhinoSystemDir.TrimEnd('\', '/'))"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
$plugin = Get-Item -LiteralPath (Join-Path $OutputDirectory 'OutpatientRhino.rhp')
Write-Output $plugin.FullName
