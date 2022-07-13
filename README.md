# Doppkit for GRiD

Doppkit is a CLI for the USACE GRiD program. It supports downloading user 
exports when given an application token

```bash
$ export GRID_ACCESS_TOKEN=KMCb6Nl799EFPproLLJR8bgeqzd4q
$ doppkit --progress True list --filter "Chicago"
$ doppkit --log-level DEBUG --progress True sync 80903
```
