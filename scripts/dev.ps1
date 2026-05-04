param(
  [string]$DbPath = "data/local/fraud_v2.sqlite"
)

$env:FRAUD_SQLITE_PATH = $DbPath
uv run uvicorn fraud_v2.api.main:app --reload --host 127.0.0.1 --port 8000

