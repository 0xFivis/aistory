param(
    [string]$App = "app.main:app",
    [string]$ListenAddress = "127.0.0.1",
    [int]$Port = 8000,
    [ValidateSet("critical","error","warning","info","debug","trace")]
    [string]$LogLevel = "info",
    [switch]$Reload,
    [int]$Workers = 1,
    [string]$VirtualEnv = ".venv",
    [string[]]$ExtraArgs
)

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendSrc = Join-Path $scriptRoot "src"

if ($VirtualEnv -and -not [string]::IsNullOrWhiteSpace($VirtualEnv)) {
    if ([System.IO.Path]::IsPathRooted($VirtualEnv)) {
        $venvPath = $VirtualEnv
    } else {
        $venvPath = Join-Path $scriptRoot $VirtualEnv
    }

    $activateScript = Join-Path $venvPath "Scripts\Activate.ps1"
    if (Test-Path $activateScript) {
        Write-Host "Activating virtual environment: $venvPath" -ForegroundColor Cyan
        . $activateScript
    } else {
        Write-Warning "Virtual environment not found at $venvPath. Proceeding without activation."
    }
}

$env:PYTHONPATH = $backendSrc

if (($PSBoundParameters.ContainsKey('ListenAddress') -eq $false) -or ($PSBoundParameters.ContainsKey('Port') -eq $false)) {
    $pythonScript = @'
import json
from app.config.settings import get_settings

settings = get_settings()
print(json.dumps({
    "host": settings.API_HOST or "",
    "port": settings.API_PORT or 0
}))
'@

    $apiConfig = $null
    $tempScriptPath = $null
    try {
        $tempScriptPath = [System.IO.Path]::Combine([System.IO.Path]::GetTempPath(), "aistory_uvicorn_config_{0}.py" -f ([System.Guid]::NewGuid().ToString("N")))
        Set-Content -Path $tempScriptPath -Value $pythonScript -Encoding UTF8
        $apiConfigJson = & python $tempScriptPath
        if (-not [string]::IsNullOrWhiteSpace($apiConfigJson)) {
            $apiConfig = $apiConfigJson | ConvertFrom-Json
        }
    } catch {
        Write-Warning "无法从 .env 读取 API 配置：$_"
    } finally {
        if (Test-Path $tempScriptPath) {
            Remove-Item $tempScriptPath -ErrorAction SilentlyContinue
        }
    }

        if ($LASTEXITCODE -eq 0 -and $apiConfig) {
            if (-not $PSBoundParameters.ContainsKey('ListenAddress') -and $apiConfig.host) {
                $ListenAddress = [string]$apiConfig.host
            }
            if (-not $PSBoundParameters.ContainsKey('Port') -and $apiConfig.port -and $apiConfig.port -ne 0) {
                $Port = [int]$apiConfig.port
            }
            if (-not $PSBoundParameters.ContainsKey('ListenAddress') -or -not $PSBoundParameters.ContainsKey('Port')) {
                Write-Host ("Using settings-defined address {0}:{1}" -f $ListenAddress, $Port) -ForegroundColor DarkGray
            }
        }
}

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Error "Could not locate 'python' on PATH. Activate your virtual environment first."
    exit 1
}

$uvicornArgs = @(
    "-m", "uvicorn",
    $App,
    "--host", $ListenAddress,
    "--port", $Port,
    "--log-level", $LogLevel
)

if ($Reload.IsPresent) {
    $uvicornArgs += "--reload"
}

if ($Workers -gt 1) {
    $uvicornArgs += @("--workers", $Workers)
}

if ($ExtraArgs) {
    $uvicornArgs += $ExtraArgs
}

Write-Host "Starting Uvicorn..." -ForegroundColor Cyan
Write-Host "  App:       $App" -ForegroundColor DarkGray
Write-Host "  Host:      $ListenAddress" -ForegroundColor DarkGray
Write-Host "  Port:      $Port" -ForegroundColor DarkGray
Write-Host "  Log level: $LogLevel" -ForegroundColor DarkGray
if ($Reload.IsPresent) {
    Write-Host "  Reload:    Enabled" -ForegroundColor DarkGray
}
if ($Workers -gt 1) {
    Write-Host "  Workers:   $Workers" -ForegroundColor DarkGray
}

& python @uvicornArgs

if ($LASTEXITCODE -ne 0) {
    Write-Error "Uvicorn exited with code $LASTEXITCODE"
    exit $LASTEXITCODE
}
