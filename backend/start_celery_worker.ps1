param(
    [int]$Concurrency = 4,
    [string]$Queue = "default",
    [ValidateSet("info","debug","warning","error","critical")]
    [string]$LogLevel = "debug",
    [string]$Pool = "threads",
    [string]$VirtualEnv = ".venv"
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

        # Ensure CUDA/cuDNN binaries installed via pip are on PATH for this session.
        $pythonScript = @"
import json
import pathlib
import sys

try:
    import nvidia.cudnn as cudnn
except ImportError:
    sys.exit(0)

base = pathlib.Path(cudnn.__file__).resolve().parent
nvidia_root = base.parent
candidates = [
    base / 'bin',
    nvidia_root / 'cublas' / 'bin',
    nvidia_root / 'cuda_nvrtc' / 'bin',
    nvidia_root / 'cuda_runtime' / 'bin',
]

print(json.dumps([str(path) for path in candidates if path.exists()]))
"@

        $cudaPathJson = & python -c $pythonScript

        if ($cudaPathJson) {
            try {
                $binsToAdd = @()
                $candidatePaths = $cudaPathJson | ConvertFrom-Json
                if ($candidatePaths -is [string]) {
                    $candidatePaths = @($candidatePaths)
                }

                foreach ($candidate in $candidatePaths) {
                    if ($candidate -and (Test-Path $candidate)) {
                        $binsToAdd += [string]$candidate
                    }
                }

                if ($binsToAdd.Count -gt 0) {
                    $existingPathEntries = $env:PATH -split ';'
                    $env:PATH = (($binsToAdd + $existingPathEntries) |
                        Where-Object { $_ -and $_.Trim() } |
                        Select-Object -Unique) -join ';'
                }
            } catch {
                Write-Warning "Failed to merge CUDA/cuDNN paths into PATH: $_"
            }
        }
    } else {
        Write-Warning "Virtual environment not found at $venvPath. Proceeding without activation."
    }
}

$env:PYTHONPATH = $backendSrc
if (-not $env:LOG_LEVEL -or [string]::IsNullOrWhiteSpace($env:LOG_LEVEL)) {
    $env:LOG_LEVEL = "DEBUG"
}

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Error "Could not locate 'python' on PATH. Activate your virtual environment first."
    exit 1
}

$celeryArgs = @(
    "-m", "celery",
    "-A", "app.celery_app.celery_app",
    "worker",
    "--pool", $Pool,
    "--concurrency", $Concurrency,
    "--loglevel", $LogLevel,
    "-Q", $Queue
)

Write-Host "Starting Celery worker..." -ForegroundColor Cyan
Write-Host "  Pool:        $Pool" -ForegroundColor DarkGray
Write-Host "  Concurrency: $Concurrency" -ForegroundColor DarkGray
Write-Host "  Queue:       $Queue" -ForegroundColor DarkGray
Write-Host "  Log level:   $LogLevel" -ForegroundColor DarkGray

& python @celeryArgs

if ($LASTEXITCODE -ne 0) {
    Write-Error "Celery exited with code $LASTEXITCODE"
    exit $LASTEXITCODE
}
