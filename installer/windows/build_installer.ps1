$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$IssFile = Join-Path $ScriptDir "PRPFinanceiroInstaller.iss"

$iscc = Get-Command ISCC.exe -ErrorAction SilentlyContinue
if (-not $iscc) {
    $default = "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
    if (Test-Path $default) {
        $isccPath = $default
    } else {
        throw "ISCC.exe nao encontrado. Instale o Inno Setup 6."
    }
} else {
    $isccPath = $iscc.Source
}

& $isccPath $IssFile
Write-Host "Installer gerado com sucesso em: $ScriptDir"

