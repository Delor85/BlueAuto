# BIR — Commercial shell and delivery register (2026-10-15)

## Source and scope
Candidate branch: feat/bir-v2-9-9-6-ai-guide-harmonization, PR #74 remains draft pending full qualification.
Original logo: app/src/main/assets/bir-logo.svg — unchanged.
Release identity remains 2.9.9.6/vc70 *candidate*; no claim of permanent APK or installed deployment.
No Worker/D1/migrations, USSD execution, finance, PIN or ownership changes in this UI commit.

## Delivered in source
- ES5/Android 6-compatible additive commercial home; role-aware PoS/DSM/DAE sale/buy/supply.
- Reuses existing live financial forms and Android bridge; no duplicate transaction engine.
- Robot quick diagnosis reads local real native configuration and opens official SIM/permissions/PIN/start/battery tools.
- Account switch from existing account chip; original BIR logo and Blue colors kept.
- Commerce form focused as a subpage; history navigation via same-WebView state, old dashboards accessible separately.
- Advertising placeholder **only**, no ad network or data collection.
- Forum placeholder **only**, no user posting, stored content, moderation or external access.
- Legacy network/accounting/AI/War Rooms retained; AI rail and assistant reply access explicitly restored through Dashboard routing; no new financial accounting engine in this commit.

## Follow-up scope (NOT delivered by this commit)
1. PIN watchdog: cancel verified telephony dialog after 120–180s, prove session closed, then test *825*3*3# safely; never auto-replay uncertain finance.
2. Robot continuity: separate configured/active/connected/ready, Android swipe/sleep test, never bypass secure lock.
3. Reconcile terminal server side effects idempotently and persist offline receipts before cleanup.
4. Fully audited USSD catalog (balance child, own balance, history, detail, freeze/change/reset PIN) with operation-specific acceptance.
5. Account/parent/child double-entry business ledger, exact commission ownership, no double counting or synthetic profit.
6. Assistant BIR AI voice and verified context; no PIN in transcript or automatic finance.
7. Full standalone forum with opt-in identity/moderation/reporting and ads with partner consent/compliance.
8. Permanent signed APK update compatible with historic certificate, validation Android 6/11/16, promotion through release governance.

## Acceptance tests
Run: node --check app/src/main/assets/commercial-shell-v2996.js
Run: node app/src/test/v2996-commercial-shell-contract.mjs
Run inherited v2996 qualification workflows, isolated APK and device smoke.
Check PoS: Vendre/Acheter, no child supply. DSM: Approvisionner PoS/Acheter. DAE: Approvisionner DSM.
Check immediate account change, read-only Robot actions, screen state, input preservation, Back behavior, no ad/forum writes.
Do not assert deployed until signed permanent APK, SHA, install-over-old-version check and device test are recorded.

## Additional source hardening
- RobotService watches expired active USSD and requests one guarded phone-only Annuler click (with command-ID fence), then records UNKNOWN. It **does not** prove session closure and **does not** auto-compose a new transaction or even the SIM test.
- User must verify the phone dialog is closed before manually selecting existing TEST_NUMBER *825*3*3#. If the line responds, the financial transfer still needs reconciliation.
- These safeguards require emulator and Android 6/11 telephony-field qualification; currently source-delivered only.
