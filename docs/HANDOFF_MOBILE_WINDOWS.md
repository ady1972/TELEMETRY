# GOATS Telemetry — Android / Windows handoff
Updated: 2026-11-19

## Import verification snapshot — 2026-11-15

Source archives for Android V0.2.1 and Windows V5.4.15.4 BURST4 have been
inspected and imported locally on `codex/mobile-windows-handoff`.
See [the verified migration report](MIGRATION_MOBILE_WINDOWS_REPORT.md)
for source provenance, implemented features, compatibility limits and actual
test/build results. The user reviewed the changes and authorized commit and
push to the handoff branch. The user subsequently explicitly requested merging
the complete application projects into `main`. Preserve the firmware updates
already present on `main` when integrating the handoff branch.
The requirements below remain historical context, not implementation claims.

## Version directories

Each complete application version lives in its own directory:

- Android V0.2.1: `mobile/v0.2.1/` (Gradle project root).
- Windows V5.4.15.4 BURST4: `windows/v5.4.15.4-burst4/` (launcher and modules).
- Windows V5.4.15.5 BURST4: `windows/v5.4.15.5-burst4/`, derived from V5.4.15.4
  with independent fullscreen visibility controls for braking analysis, corner
  speeds and the speed graph; removes the map description overlay in both views.

- Android V0.2.2: `mobile/v0.2.2/`, shared session/track folder with Windows.
- Windows V5.4.15.6: `windows/v5.4.15.6-burst4/`, shared session/track sync and
  direct USB-UART M9N constellation/output profiles. The user explicitly requested
  these GNSS receiver changes and confirmed direct UART, not a laptimer bridge.
  Rate/baud and firmware remain unchanged. See `docs/CLOUD_SYNC_MOBILE_WINDOWS.md`
  and the version README for capabilities and hardware/provider test limits.

- Android V0.2.3: `mobile/v0.2.3/`, receives Windows session deletion receipts.
- Windows V5.4.15.7: `windows/v5.4.15.7-burst4/`, managed originals, startup check
  independent of periodic sync, legacy source adoption and physical session
  deletion with receipts preventing offline copies from resurrecting files.
  These session deletions were explicitly requested by the user; track deletions
  remain local. External sources/microSD and older release folders are retained.

- Windows V5.4.15.8: `windows/v5.4.15.8-burst4/`, automatic RAM/BBR/flash
  persistence with separate storage readback, plus measurement/navigation rate
  readback. On 19 Nov the user confirmed receiver parameter application works
  but reported reversion after reboot and explicitly requested automatic flash
  saving and frequency readback. New persistence still needs a physical power
  cycle test; UART1 only, no firmware changes. Mobile V0.2.3 remains compatible.

- Windows V5.4.15.9: `windows/v5.4.15.9-burst4/`, adds the already-read
  GNSS frequency, period, NAV divisor and UART1 baud to the log summary. The user
  confirmed the selector updates correctly and requested the same data in the log.
  Receiver backend and persistence are identical to V5.4.15.8.

- Windows V5.4.15.10: `windows/v5.4.15.10-burst4/`, adds 2x, 5x and 10x
  replay options in Analisi and fullscreen. The S shortcut cycles all five speeds.
  Replay timing/interpolation, receiver configuration, storage and protocols
  remain unchanged; default playback remains 1x.

- Windows V5.4.15.11: `windows/v5.4.15.11-burst4/`, enables NAV-SAT near 1 Hz
  and NAV-DOP each navigation epoch alongside NAV-PVT in UBX profiles. The user
  agreed after discussion of satellite data and current telemetry compatibility.
  SAT divider is derived from receiver MEAS/NAV and adjusted on rate changes.
  Firmware inspection correction: current Guition RC2 is passive too; its header
  setup helper contains 25/25/1 Hz but is NOT called at boot. Both Guition RC2 and
  RLCD TEST26/RC2 decode SAT/DOP and depend on receiver configuration. No firmware
  modifications; actual message output still needs receiver testing.

The platform-level READMEs list available versions. Keep each source package
complete when adding a new version; do not infer complete older releases from
the historical standalone scripts bundled in the Windows package.

## Status and provenance
This document captures requirements and earlier conversation decisions, NOT a verified inventory of application source code. The repository README currently primarily documents firmware. Android/Windows source paths, build systems and current implementation status must be verified before moving or changing code.

## Goal
Use the same GitHub repository for GOATS Mobile (Android) and GOATS Windows (Manager PC), with independent directories `mobile/` and `windows/` when actual sources are available. Preserve `firmware/` unchanged.

## Requirements to validate against existing sources
### Android
- Offline-first kart telemetry application.
- Import session data from lap timer over Wi-Fi (not BLE for this workflow), subject to verification of device support and protocol.
- Circuit editor compatible with Windows.
- Optional synchronization with PC/cloud; offline operation must remain possible.
- Do not confuse an earlier BLE GNSS receiver workflow with the session import workflow.

### Windows
- Manager PC for importing, viewing, comparing and deleting multiple sessions.
- Circuit management and compatibility with lap-timer track/sector formats.
- Separate session and circuit archives, with possible NAS location.
- Preserve historical file compatibility and existing features.
- Prior conversations mentioned Manager 5.4.15.4; do not assume it is the current source version.
- USB serial transfers had been slow; user previously deferred optimization until firmware stability. Do not change transport without request.

### Cross-platform
- Inventory existing CSV formats, timestamps/timezones, session naming, sector and lap logic and device protocols from source.
- Maintain backward compatibility for stored sessions and tracks.
- Distinguish implemented, tested, requested and unknown features.
- Do not change GNSS (UBX-only 25 Hz, 230400 baud, GPS/Galileo/GLONASS/BeiDou, SBAS) as part of this app migration.

## Migration checklist
1. Locate authoritative Android and Windows source projects, including files from earlier chats or PC if not in GitHub.
2. Identify languages, build tools, versions, tests and existing release artifacts.
3. Produce a feature matrix: present / missing / uncertain, with file-level evidence.
4. Inventory CSV and transport protocols before any refactoring.
5. Add source projects to separate directories without overwriting firmware.
6. Build baseline versions, compare behavior, then implement prioritized changes on separate branches.
7. Record decisions and tested results in docs, and use PR review before merge.

## Explicit non-goals of this handoff
- No firmware modification.
- No assumption that all historical chats or ZIP attachments are automatically accessible to Codex.
- No declaration that application features are implemented without inspecting their source.
