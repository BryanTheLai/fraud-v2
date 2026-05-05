# Code Factory Receipts

The active dashboard is `dashboard.md`.

Completed task cards and run records were archived to keep the current tree
small while preserving the original proof files losslessly.

Archive:

```text
factory/archive/code-factory-receipts-20260504-20260505.zip
```

Contents:

- `runs/RR-20260504-001.md` through `runs/RR-20260505-047.md`
- `tasks/done/TC-20260504-001-*.md` through `TC-20260504-002-*.md`
- `tasks/review/TC-20260505-001-*.md` through `TC-20260505-047-*.md`

Integrity:

```text
SHA256 AECB90CCA34FF1818F2717E96CCAAAD57365B2B05281D2D36BFDC2E2A1C5A04A
```

Restore:

```powershell
Expand-Archive -LiteralPath factory\archive\code-factory-receipts-20260504-20260505.zip -DestinationPath factory -Force
```
