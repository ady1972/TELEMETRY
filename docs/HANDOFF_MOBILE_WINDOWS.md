# GOATS Telemetry — Android / Windows handoff
Updated: 2026-11-15

## Import verification snapshot — 2026-11-15

Source archives for Android V0.2.1 and Windows V5.4.15.4 BURST4 have been
inspected and imported locally on `codex/mobile-windows-handoff`.
See [the verified migration report](MIGRATION_MOBILE_WINDOWS_REPORT.md)
for source provenance, implemented features, compatibility limits and actual
test/build results. The user reviewed the changes and authorized commit and
push to the handoff branch. No merge to `main` is part of this migration.
The requirements below remain historical context, not implementation claims.

## Version directories

Each complete application version lives in its own directory:

- Android V0.2.1: `mobile/v0.2.1/` (Gradle project root).
- Windows V5.4.15.4 BURST4: `windows/v5.4.15.4-burst4/` (launcher and modules).

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
