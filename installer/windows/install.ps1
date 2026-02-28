$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Resolve-Path (Join-Path $ScriptDir "..\..")
$EnvFile = Join-Path $ProjectRoot ".env.prod"
$EnvExample = Join-Path $ProjectRoot ".env.prod.example"
$RuntimeDir = Join-Path $ProjectRoot "runtime"

function Test-Command($Name) {
    return [bool](Get-Command $Name -ErrorAction SilentlyContinue)
}

function New-RandomHex([int]$bytes = 32) {
    $buffer = New-Object byte[] $bytes
    [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($buffer)
    return ($buffer | ForEach-Object { $_.ToString("x2") }) -join ""
}

function Set-Or-AddEnvValue([string]$Path, [string]$Key, [string]$Value) {
    $content = Get-Content -Path $Path
    $pattern = "^$([regex]::Escape($Key))="
    $found = $false
    for ($i = 0; $i -lt $content.Count; $i++) {
        if ($content[$i] -match $pattern) {
            $content[$i] = "$Key=$Value"
            $found = $true
            break
        }
    }
    if (-not $found) {
        $content += ""
        $content += "$Key=$Value"
    }
    Set-Content -Path $Path -Value $content
}

Write-Host "==> Validando prerequisitos..."
if (-not (Test-Command "docker")) {
    throw "Docker nao encontrado. Instale Docker Desktop e tente novamente."
}

docker compose version | Out-Null

if (-not (Test-Path $EnvFile)) {
    if (-not (Test-Path $EnvExample)) {
        throw ".env.prod e .env.prod.example nao encontrados."
    }
    Copy-Item $EnvExample $EnvFile
    Write-Host "==> Arquivo .env.prod criado a partir do exemplo."
}

Write-Host "==> Preparando variaveis de ambiente..."
Set-Or-AddEnvValue -Path $EnvFile -Key "PRP_ROOT_DIR" -Value "./runtime"

$envContent = Get-Content -Path $EnvFile -Raw
if ($envContent -notmatch "(?m)^APP_BIND_IP=") {
    Set-Or-AddEnvValue -Path $EnvFile -Key "APP_BIND_IP" -Value "127.0.0.1"
}
if ($envContent -notmatch "(?m)^APP_PUBLIC_HOST=") {
    Set-Or-AddEnvValue -Path $EnvFile -Key "APP_PUBLIC_HOST" -Value "localhost"
}
if ($envContent -match "(?m)^SECRET_KEY=(|prod_key_change_me)$") {
    Set-Or-AddEnvValue -Path $EnvFile -Key "SECRET_KEY" -Value (New-RandomHex)
}
if ($envContent -match "(?m)^UPDATE_TOKEN=(|prp_secure_token_2026)$") {
    Set-Or-AddEnvValue -Path $EnvFile -Key "UPDATE_TOKEN" -Value (New-RandomHex)
}

Write-Host "==> Criando diretorios locais..."
New-Item -ItemType Directory -Force -Path (Join-Path $RuntimeDir "postgres") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $RuntimeDir "data") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $RuntimeDir "manifests") | Out-Null

Write-Host "==> Baixando imagens..."
docker compose `
  --env-file $EnvFile `
  -f (Join-Path $ProjectRoot "docker-compose.prod.yml") `
  -f (Join-Path $ProjectRoot "docker-compose.prod.override.yml") `
  pull

Write-Host "==> Subindo servicos..."
docker compose `
  --env-file $EnvFile `
  -f (Join-Path $ProjectRoot "docker-compose.prod.yml") `
  -f (Join-Path $ProjectRoot "docker-compose.prod.override.yml") `
  up -d

Write-Host "==> Instalacao finalizada."
Write-Host "Aplicacao: http://localhost:5000"
