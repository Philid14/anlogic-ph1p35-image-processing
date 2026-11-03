# TARGET verification run

Independent checks: **PASS**; integration ready: **NO**.
Profile: `handoff`. HEAD: `e71b0696a09bfe3a57b0ccccc0d429aaf793cca4`. Source stable: `True`.
A dirty worktree is identified below; source LF hashes are in summary.json.

```text
clean
```

| Check | Kind | Result | Exit | Log |
|---|---|---|---:|---|
| class_models | CHECK | PASS | 0 | [class_models.log](class_models.log) |
| contract | CHECK | PASS | 0 | [contract.log](contract.log) |
| data_contract | CHECK | PASS | 0 | [data_contract.log](data_contract.log) |
| class_rtl | CHECK | PASS | 0 | [class_rtl.log](class_rtl.log) |
| track_audit | CHARACTERIZATION | MATCHED / OPEN | 0 | [track_audit.log](track_audit.log) |
| text_updates | CHECK | PASS | 0 | [text_updates.log](text_updates.log) |
| legacy_chain | CHECK | PASS | 0 | [legacy_chain.log](legacy_chain.log) |
| classifier | CHECK | PASS | 0 | [classifier.log](classifier.log) |
| detector | CHECK | PASS | 0 | [detector.log](detector.log) |
| geometry | CHECK | PASS | 0 | [geometry.log](geometry.log) |
| track_regression | CHECK | PASS | 0 | [track_regression.log](track_regression.log) |
| real_font | CHECK | PASS | 0 | [real_font.log](real_font.log) |
| rgb_replay | CHECK | PASS | 0 | [rgb_replay.log](rgb_replay.log) |
| frame_transactions | CHECK | PASS | 0 | [frame_transactions.log](frame_transactions.log) |
| guard | CHECK | PASS | 0 | [guard.log](guard.log) |
| display_transactions | CHECK | PASS | 0 | [display_transactions.log](display_transactions.log) |

## Unclosed engineering gates

- A2 standalone guard: **PASS** (integration/TRACK_GUARD_INTERFACE.md; not a display freshness proof).
- Unwrapped legacy TRACK identity / age: **OPEN** (integration/TRACK_ADMISSION_PROPOSAL.md).
- MAIN normalization / CDC / DDR / atomic display: **OPEN** (integration/MAIN_CONTRACT_DRAFT.md).
- Integrated TARGET P&R and bit: **NOT_RUN** (No TARGET in current main TD entry).
- Real camera policy / thresholds: **PENDING_MATERIAL** (User reserved decision until real camera material).
- Board acceptance: **NOT_RUN** (board/OBSERVATION_GUIDE.md).

## Current TRACK gaps

- DUPLICATE: OPEN: duplicate frame confirms target; admission owner not implemented
- REORDER: OPEN: decreasing identities accepted; ordering owner not implemented
- INVALID_RUN: OPEN: no observation age mechanism; no approved timeout value
- SILENCE: OPEN: no wall-clock expiry; 20 cycles are a fixture, not an approved limit
- SESSION_INVALID: OPEN: session clear requires valid strobe; explicit epoch authority absent
- OLD_SESSION_RETURN: OPEN: retired session can re-enter through a valid result

Full argv, source hashes, durations and structured results: [summary.json](summary.json).
No physical CDC, integrated timing, camera accuracy or board result is established.
