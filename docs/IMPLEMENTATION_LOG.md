# SDD ledger — plan: docs/superpowers/plans/2026-09-27-local-web-ui.md
Base: ad2c759. User changes copied without modifying original checkout.
Pre-flight: models→store→listener→API→frontend use consistent snapshots/revisions.
Pre-flight: events→WebSocket→frontend use instance_id and numeric event id.
Pre-flight: keyboard→listener Stop disables before await; generation fences pending actions.
Pre-flight: session→launcher→frontend launch token plus GET session supports refresh.
Pre-flight: backend→Qt uses queued signals and futures, never widgets from asyncio.
Ruling: Keep previous GUI files intact until platform acceptance; new main uses launcher. Cost: temporary dead GUI code.
Ruling: Missing Windows host/live TikTok credentials do not stop implementation; mark those acceptance checks NOT RUN, no release claim.
Tasks 1–14: pending.
Tasks 1–2: implemented; RED missing modules → GREEN 13 tests. Core config path is injected; old config API left intact for existing GUI.
Ruling: Python >=3.12 with local validation on 3.14.7; resolved package versions pinned. Windows version compatibility remains acceptance work.
Tasks 3–6: core paths implemented, RED missing modules → GREEN 20 tests overall. Extended error/adapter/diagnostic checks remain before acceptance.
Task 7: HTTP/API implemented. TestClient websocket defaults to testserver even with base_url; corrected test to explicit ws://127.0.0.1:8000. Host enforcement unchanged.
Task 8: real HTTP health/start/shutdown and second-instance tests pass. Fixed reproducible Qt socket destructor crash by replacing lambda capturing socket with QObject receiver slot; desktop suite 3 passed.
Tasks 9–13: implementation present. Backend 35 tests, frontend 8 tests, TypeScript/Vite build PASS. PyInstaller macOS .app PASS and native launch opens browser. Browser UI editing+refresh and 900x550 PASS. Task 14 local automated/integration checks PASS; Windows, physical LIVE/keys, signing and clean-machine acceptance NOT RUN.
Ruling: Group related implementation tasks into coherent commits and modules rather than empty wrappers; no change to behavior. Cost: coarser history than planned.
Ruling: Legacy Qt views/config APIs retained unchanged to preserve user edits; new entrypoint uses injected ConfigStore and resources paths. Cost: old unused code remains until acceptance.
Final review: fresh gpt-6-astra reviewer, whole branch ad2c759..4a51a4c. Five Important findings, zero Critical/Minor.
Final: fixed shared-cookie CSRF invalidation — test_second_launch_preserves_first_tab_csrf RED→GREEN.
Final: fixed repeated Stop cancelling cleanup — test_repeated_stop_does_not_cancel_disconnect_cleanup RED→GREEN.
Final: fixed stale generation keyboard error — service and worker race tests RED→GREEN.
Final: fixed disconnected panel presenting active status — App.test.tsx RED→GREEN.
Final: fixed TikTok HTTP session leak — cancelled/normal disconnect close tests RED→GREEN.
Final: fixed unwritable data directory escaping native error dialog — launcher regression RED→GREEN.
Final suite: Python 42/42; frontend 9/9; TypeScript/Vite build PASS.
Final: Ruling: review excludes original uncommitted GUI changes — preserved without changes, not part of shipped new entrypoint; cost: legacy bugs remain only in old code.
Final: Ruling: external platform/live/signing checks remain NOT RUN — no Windows/live integration environment; cost: not a production-ready cross-platform release yet.
Final: Ruling: already-started native keyboard invocation may finish after Stop — spec explicitly permits this and executor fences pending work; cost: at most an in-flight invocation continues.

Final packaging: macOS .app and DMG PASS; final packaged multi-tab save PASS. Native tray manual inspection NOT RUN (automation timeout); programmatic lifecycle tested. No deferred minor review findings.
