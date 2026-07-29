# Session env: E: caches only (not PYTHONPATH).
# After `uv sync`, use `uv run pra-*` — see AGENTS.md.

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$WorkspaceCache = "E:\IT_SPACES\AI\.cache"
$ProjectCache = Join-Path $ProjectRoot ".cache"

$env:HF_HOME = Join-Path $ProjectCache "huggingface"
$env:HF_HUB_CACHE = Join-Path $env:HF_HOME "hub"
$env:HF_HUB_DISABLE_TELEMETRY = "1"
$env:HF_HUB_DISABLE_SYMLINKS_WARNING = "1"
$env:UV_CACHE_DIR = Join-Path $WorkspaceCache "uv"
$env:PIP_CACHE_DIR = Join-Path $WorkspaceCache "pip"
$env:TMP = Join-Path $ProjectCache "tmp"
$env:TEMP = $env:TMP
$env:TRANSFORMERS_CACHE = Join-Path $env:HF_HOME "transformers"
$env:SENTENCE_TRANSFORMERS_HOME = Join-Path $env:HF_HOME "sentence_transformers"
$env:PRA_PROJECT_ROOT = $ProjectRoot

# Avoid OpenBLAS/MKL import deadlock (Streamlit/pyarrow hang on this machine).
$env:OMP_NUM_THREADS = "1"
$env:OPENBLAS_NUM_THREADS = "1"
$env:MKL_NUM_THREADS = "1"
$env:NUMEXPR_NUM_THREADS = "1"
$env:PYTHONNOUSERSITE = "1"

foreach ($dir in @($env:HF_HOME, $env:HF_HUB_CACHE, $env:UV_CACHE_DIR, $env:PIP_CACHE_DIR, $env:TMP)) {
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
}

Write-Host "E: drive env active (no C: cache/temp)"
Write-Host "  HF_HOME      = $env:HF_HOME"
Write-Host "  UV_CACHE_DIR = $env:UV_CACHE_DIR"
Write-Host "  TMP/TEMP     = $env:TMP"
