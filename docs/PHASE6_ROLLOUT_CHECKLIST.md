# Phase 6 Rollout Checklist

Date: 2026-03-20

## Phase 6 Todo and Status

1. Startup self-heal gate before app unlock  
Status: completed  
Progress: 100%

2. Queued/stalled recovery tuning and force-start behavior  
Status: completed  
Progress: 100%

3. Health diagnostics and download engine reset flow  
Status: completed  
Progress: 100%

4. Regression pass and rollout validation  
Status: completed  
Progress: 100%

5. Core Stability (6F) — Sleep detection, watchdog, auto-restart, port fallback  
Status: completed  
Progress: 100%

## Go-Live Validation Steps

1. Launch app and confirm status bar reaches:
   - `Backend Online`
   - `aria2 running`

2. Confirm startup self-heal lock behavior:
   - On cold start, actions are disabled until checks pass.
   - After checks pass, actions are enabled automatically.

3. Confirm mandatory update flow still works:
   - Forced lock dialog appears when `minimum_required_version` is higher.
   - Retry and installer link fallback are available if download stalls.

4. Confirm engine recovery actions:
   - `Reset Engine` restores backend/aria2 when they go offline.
   - `Force Start` can wake a queued/stalled item.

5. Confirm no startup regressions:
   - `Add Magnet`, `Pause All`, `Resume All`, and `Settings` work after unlock.
   - Downloads list refreshes without disappearing rows.
   - Run `packaging/validate_phase6_runtime.ps1` and confirm PASS.

## Publish Reminder (Desktop)

Desktop release updates should be published with local workflow + R2:

1. Build locally:
   - `powershell -ExecutionPolicy Bypass -File .\packaging\build_nuitka.ps1`
2. Validate upload artifacts:
   - `StreamoreSetup.exe`
   - `latest.json`
3. Verify `latest.json` and installer URL are reachable from R2.
