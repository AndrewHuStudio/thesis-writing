param([Parameter(Mandatory=$true)][string]$Draft)
$ErrorActionPreference = 'Stop'
$draftPath = [System.IO.Path]::GetFullPath($Draft)
$qaPath = Join-Path $PSScriptRoot 'render'
New-Item -ItemType Directory -Path $qaPath -Force | Out-Null
$pdfPath = Join-Path $qaPath 'section.pdf'
$wpsApp = New-Object -ComObject KWPS.Application
$draftDocument = $null
try {
    $draftDocument = $wpsApp.Documents.Open($draftPath, $false, $true)
    $draftDocument.Repaginate()
    $draftDocument.ExportAsFixedFormat($pdfPath, 17)
    Write-Output $pdfPath
}
finally {
    if ($null -ne $draftDocument) {
        $draftDocument.Close(0)
        [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($draftDocument)
    }
    [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($wpsApp)
}
