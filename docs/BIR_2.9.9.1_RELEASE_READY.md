# B.I.R. 2.9.9.1 — Release readiness

- Application branch: `fix/bir-v2-9-9-1-field-runtime`
- Base application source: `a13bafc76aa23157bb409a72904f4bc64f5cf815` (2.9.9)
- Release identity: `2.9.9.1` / versionCode `65`
- Production boundary: APK-only; no Worker deployment, no D1 migration, no merge.
- Permanent signing key remains outside GitHub and must never be committed or uploaded as an Actions artifact.
- Permanent APK may be produced only after the exact qualification payload passes the Android matrix and is then re-signed locally with the historical certificate `f51e1d84271d3c4e229ce3cb424b36c8d564832b939e496bfc50352339b769b5`.
