# NoLeftClickRotation — Candidate 1

- Status: user-tested candidate, directly overwritten as requested
- Target: ZBrush 2026.1.1.1 on Windows
- Source: `NoLeftClickRotation.py`
- SHA-256: `9DE819E92A349D907AA02AE73AD26AC9584939382F7881D1A2DB5FC2A36B4D1D`
- LightBox behavior: query `Preferences:LightBox:LightBox` flags on every left-button down. Bit `0x4` is treated as the LightBox toggle edge; the common `0x8` bit is not treated as visibility. No LightBox View Window ID is used.
- Other behavior: stable PixolPick material-buffer query, blank-canvas hold-and-bridge sculpt start, Edit-mode camera lock, right-button temporary unlock, and a minimum 10ms relock delay after right-button release.
