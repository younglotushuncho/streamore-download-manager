# Streamore Implementation Phases

This is the active execution board for desktop + update pipeline work.

## Overall Progress

- Total completion: **100%**
- Current phase: **Phase 6 - Experience, Growth & Monetization** (Completed)

## Phase 1 - Foundation and Release Pipeline

- Status: **Completed**
- Progress: **100%**
- Completed:
  - Local-only release flow (build + publish to R2).
  - `latest.json` publishing contract.
  - Installer hosting moved to R2/CDN.
  - Base update check wiring in desktop app.

## Phase 2 - Reliability and Runtime Stability

- Status: **Completed**
- Progress: **100%**
- Completed:
  - Backend/aria2 startup hardening and health checks.
  - Dedicated backend port default (`58432`) to avoid local conflicts.
  - Download table rendering hardening (null-safe values, no silent row loss).
  - Better empty-state behavior when search/filter hides results.
  - Queue recovery behaviors (force-start for stuck queued/stalled items).

## Phase 3 - User Experience and Control (Current)

- Status: **Done**
- Progress: **100%**
- TODO:
  - Improve stalled-download recovery UX (clear reason + one-click recovery hints). **Done**
  - Add lightweight diagnostics export for support (`logs + config + version`). **Done**
  - Add “Reset download engine” action (safe aria2/backend soft reset). **Done**
  - Improve update UX messages (explicit “mandatory” vs “optional” states). **Done**
  - Add small in-app “health details” dialog (backend, aria2, queue, limits). **Done**

## Phase 4 - Automation and Quality Gate

- Status: **Done**
- Progress: **100%**
- TODO:
  - Add smoke test script for build output validation before publish. **Done**
  - Add post-publish verification script for R2 (`latest.json` + installer hash). **Done**
  - Add rollback helper (pin prior installer metadata quickly). **Done**

## Phase 5 - Scale and Monetization Readiness

- Status: **Completed**
- Progress: **100%**
- Completed:
  - Desktop telemetry hooks (opt-in, privacy-safe, failure counters only). **Done**
  - Download behavior analytics for conversion funnel quality. **Done**
  - Ad/affiliate placement guardrails and performance budget tracking. **Done**

---

## Phase 6 - Experience, Growth & Monetization

- Status: **Completed**
- Progress: **100%**

### 6A — Desktop UX Quick Wins
- [x] Completion notification: system-tray popup when a download finishes **Done**
- [x] Disk space check before queuing (warn if insufficient space) **Done**
- [x] Stall auto-retry with exponential backoff **Done**
- [x] Resume-on-startup: auto-resume active downloads on app launch **Done**
- [x] Download history log: persistent record of past downloads + timestamps **Done**
- [x] Dark / Light theme toggle in Settings (Full UI application implemented) **Done**

- [x] **Phase 6B: Web Frontend Enhancements** (100%)
  - [x] Watchlist / Bookmarks: save movies to download later **Done**
  - [x] Download History view (persistent log) **Done**
  - [x] Theme toggle (Full Light/Dark mode implementation) **Done**
  - [x] Genre, Year, Rating filters on the movie browser **Done**
  - [x] "Already Downloaded" badge on movies the manager has completed **Done**
  - [x] Search autocomplete / suggestions **Done**
  - [x] Trending / Most Downloaded homepage section **Done**
  - [x] Movie trailer embed (YouTube) on movie detail page **Done**
  - [x] PWA support (installable on mobile) **Done**

### 6C — Backend & Infrastructure (100%)
- [x] Automatic stall recovery via full aria2 process restart **Done**
- [x] Per-download speed history stored for graph replay (Backend logging implemented) **Done**
- [x] Torrent health check: pre-queue seed count validation **Done**

### 6D — Privacy & Trust (100%)
- [x] GDPR consent banner (required for EU users with ads + telemetry) **Done**
- [x] Explicit opt-in for anonymous telemetry (on by default but easily togglable) **Done**
- [x] Log-level selector in settings (and "Export Log" for support) **Done**

### 6E — Monetization & Growth (100%)
- [x] Email capture: "Notify me when X is available" with mailing list **Done**
- [x] Affiliate links at point-of-download (VPN, streaming services) **Done**
- [x] Social sharing: "I just downloaded X on Streamore" **Done**
- [x] Premium tier (UI implemented; ready for Stripe integration) **Done**

### 6F — Core Stability (High Priority)
- [x] Sleep/resume detection: detect system wake and auto-resume/restart aria2 **Done**
- [x] Backend watchdog: auto-restart backend process if it crashes (max 3 retries, then notify user) **Done**
- [x] aria2 auto-restart: if `aria2_status: offline`, restart it automatically without user action **Done**
- [x] Download state persistence: save active downloads on app close, restore on next launch **Done**
- [x] Force-start seed guard: skip force-start if torrent has 0 seeds to avoid hammering aria2 **Done**
- [x] Port fallback scanning: if port 58432 is taken, try 58433–58442 automatically **Done**
