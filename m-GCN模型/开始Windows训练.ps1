param(
    [string]$Device = 'cuda:1',
    [int]$Epochs = 120
)
$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$trainingPython = Join-Path $repoRoot '.venv\gcn-win\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $trainingPython)) {
    throw 'Training environment is missing. See docs/Windows-GCN-training.md.'
}
$logDirectory = Join-Path $repoRoot '.venv\training-logs'
New-Item -ItemType Directory -Force -Path $logDirectory | Out-Null
$stamp = [DateTimeOffset]::UtcNow.ToOffset([TimeSpan]::FromHours(8)).ToString('yyyyMMdd_HHmmss_fff')
$outputLog = Join-Path $logDirectory ($stamp + '.log')
$errorLog = Join-Path $logDirectory ($stamp + '.error.log')
$runner = Join-Path $PSScriptRoot 'relation_prediction\windows_batch.py'
$processArguments = '-X utf8 "' + $runner + '" --device ' + $Device + ' --epochs ' + $Epochs
$trainingProcess = Start-Process -FilePath $trainingPython -ArgumentList $processArguments `
    -WorkingDirectory $repoRoot -WindowStyle Hidden -PassThru `
    -RedirectStandardOutput $outputLog -RedirectStandardError $errorLog
Write-Output ('PID=' + $trainingProcess.Id)
Write-Output ('LOG=' + $outputLog)
Write-Output ('ERROR_LOG=' + $errorLog)
