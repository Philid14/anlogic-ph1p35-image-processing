# 独立故障注入矩阵（拟议契约，非MAIN实现证明）

本矩阵由本轮实际执行的 `contract-model-final.json` 生成，每项保存具体输入、独立硬期望、不变量和失败条件。
测试时间均为夹具参考tick；跨域使用独立事件边沿调度，未仿真物理同步器或亚稳态。
当前生产TRACK另有六项OPEN_GAP，不能以本模型通过关闭；详见A2方案和track-audit.json。

| 类别 | 覆盖边界 |
|---|---|
| 1 重复/乱序/回绕 | 独立事件/政策模型；硬件待实现 |
| 2 session重启 | 独立事件/政策模型；硬件待实现 |
| 3 光栅标记/截断/取消 | 独立事件/政策模型；硬件待实现 |
| 4 最后lane/部分尾拍 | 最后lane几何gold不是DUT测试；真实RTL边界另由本轮完整RGB/检测回归覆盖。部分尾拍在现有端口不可辨识 |
| 5 结果晚到/缺失 | 独立事件/政策模型；硬件待实现 |
| 6 DDR槽代次/覆盖 | 独立事件/政策模型；硬件待实现 |
| 7 重复显示/跳帧 | 独立事件/政策模型；硬件待实现 |
| 8 CDC复位/服务 | 抽象整包/epoch/容量模型；不是异步FIFO或CDC时序验证 |
| 9 图文原子提交 | 独立事件/政策模型；硬件待实现 |
| 10 观测年龄/超时 | 独立事件/政策模型；硬件待实现 |

| # / 类别 | 注入与输入 | 独立期望 | 不变量 / 失败条件 | 实际结果 |
|---|---|---|---|---|
| 1 / 1 identity_duplicate_and_reorder | `{"frames":[10,10,9,11],"time":[1,2,3,4]}` | `[["positive",1,1,0,false],["duplicate",1,1,0,false],["out_of_order",1,1,0,false],["positive",2,2,0,true]]` | Only unique increasing identities may advance observations or acquisition; observed≠expected即失败 | 符合示例契约 |
| 2 / 1 frame_gap_is_not_fabricated_misses | `{"frames":[10,12]}` | `[["positive",1,1,0,false],["positive",2,2,0,true]]` | Frame gaps are transport/age facts, not fabricated no-target observations; observed≠expected即失败 | 符合示例契约 |
| 3 / 2 session_restart_and_late_old_session | `{"start_session":7,"late_packet":[1,99],"new_packet":[7,0]}` | `[["wrong_session",0,0,0,false],["positive",1,1,0,false]]` | Only explicit session authority changes epoch; old packets cannot restart tracking; observed≠expected即失败 | 符合示例契约 |
| 4 / 2 session_reuse_rejected | `{"reuse_session":7}` | `"session_reuse_without_retirement"` | No session token reuse while old associations can exist; observed≠expected即失败 | 符合示例契约 |
| 5 / 1 same_session_wrap_rejected | `{"frames":[4294967295,0]}` | `[["positive",1,1,0,false],["out_of_order",1,1,0,false]]` | Frame counter cannot wrap within the same session; observed≠expected即失败 | 符合示例契约 |
| 6 / 3 early_sof_quarantines_until_reset | `[{"x":0,"y":0,"sof":true,"eol":false,"eof":false,"source_lanes":4},{"x":4,"y":0,"sof":false,"eol":true,"eof":false,"source_lanes":4},{"x":0,"y":1,"sof":true,"eol":false,"eof":false,"source_lanes":4},{"x":4,"y":1,"sof":false,"eol":true,"eof":true,"source_lanes":4}]` | `["beat","beat","early_sof_requires_reset","needs_reset"]` | Premature SOF must not silently relabel old line state; observed≠expected即失败 | 符合示例契约 |
| 7 / 3 wrong_eol_poison_complete_frame | `[{"x":0,"y":0,"sof":true,"eol":false,"eof":false,"source_lanes":4},{"x":4,"y":0,"sof":false,"eol":false,"eof":false,"source_lanes":4},{"x":0,"y":1,"sof":false,"eol":false,"eof":false,"source_lanes":4},{"x":4,"y":1,"sof":false,"eol":true,"eof":true,"source_lanes":4}]` | `["beat","beat","beat","invalid_frame"]` | Malformed complete raster is invalid, never a valid absence; observed≠expected即失败 | 符合示例契约 |
| 8 / 3 missing_eof_requires_explicit_recovery | `[{"x":0,"y":0,"sof":true,"eol":false,"eof":false,"source_lanes":4},{"x":4,"y":0,"sof":false,"eol":true,"eof":false,"source_lanes":4},{"x":0,"y":1,"sof":false,"eol":false,"eof":false,"source_lanes":4},{"x":4,"y":1,"sof":false,"eol":true,"eof":false,"source_lanes":4}]` | `["beat","beat","beat","missing_eof_requires_reset"]` | No valid result may be inferred from silence or missing EOF; observed≠expected即失败 | 符合示例契约 |
| 9 / 3 reset_then_complete_new_session | `{"reset":true,"new_key":[2,0]}` | `["beat","beat","beat","complete_frame"]` | Recovery starts at a complete new-session SOF; observed≠expected即失败 | 符合示例契约 |
| 10 / 4 partial_tail_is_unrepresentable | `[{"x":0,"y":0,"sof":true,"eol":false,"eof":false,"source_lanes":4},{"x":4,"y":0,"sof":false,"eol":true,"eof":false,"source_lanes":4},{"x":0,"y":1,"sof":false,"eol":false,"eof":false,"source_lanes":4},{"x":4,"y":1,"sof":false,"eol":true,"eof":true,"source_lanes":2}]` | `["beat","beat","beat","partial_tail_requires_abort"]` | V1 has no lane-valid mask: partial source beat requires rejection/abort before TARGET; observed≠expected即失败 | 符合示例契约 |
| 11 / 4 abort_on_last_beat_invalidates_frame | `[{"x":0,"y":0,"sof":true,"eol":false,"eof":false,"source_lanes":4},{"x":4,"y":0,"sof":false,"eol":true,"eof":false,"source_lanes":4},{"x":0,"y":1,"sof":false,"eol":false,"eof":false,"source_lanes":4},{"x":4,"y":1,"sof":false,"eol":true,"eof":true,"source_lanes":4,"abort":true}]` | `["beat","beat","beat","invalid_frame"]` | EOF lane data cannot override a frame abort; observed≠expected即失败 | 符合示例契约 |
| 12 / 4 last_lane_geometric_gold | `{"only_hit":[7,1],"filter":false}` | `[7,1,7,1]` | Last lane on EOF contributes; existing RTL full-frame regression provides hardware evidence; observed≠expected即失败 | 符合示例契约 |
| 13 / 5 late_result_does_not_change_active_scan | `{"display_start":3,"result_ready":4,"repeat_display":5}` | `["missing",["missing",null],"visible"]` | Late result may serve a later matching display, never update current scan; observed≠expected即失败 | 符合示例契约 |
| 14 / 5 missing_result_never_borrows_latest_box | `{"frame":[1,1],"result":null}` | `"missing"` | Missing result hides overlay; does not fabricate no-target or borrow another frame; observed≠expected即失败 | 符合示例契约 |
| 15 / 6 slot_reuse_retires_old_generation | `{"slot":0,"old":[1,1,1],"new":[2,1,2]}` | `["retired_or_incomplete","missing"]` | Slot number alone is not identity; retired generations cannot supply annotations; observed≠expected即失败 | 符合示例契约 |
| 16 / 6 overwrite_during_scan_exposes_integrity_failure | `{"write_after_select":true}` | `"slot_overwritten_during_scan"` | Selected pixel lease must remain valid; hiding overlay does not repair corrupted video; observed≠expected即失败 | 符合示例契约 |
| 17 / 7 display_repeat_and_skip | `{"display_frames":[1,1,3]}` | `["visible","visible","visible"]` | Display repetition/skip does not generate acquisition observations; observed≠expected即失败 | 符合示例契约 |
| 18 / 8 cdc_source_reset_with_inflight | `{"side":"source","old_frame":1,"new_frame":2}` | `[[1],null,2]` | Endpoint reset cancels in-flight epoch; old request/ack cannot reappear as fresh; observed≠expected即失败 | 符合示例契约 |
| 19 / 8 cdc_destination_reset_with_inflight | `{"side":"destination","old_frame":1,"new_frame":2}` | `[[1],null,2]` | Endpoint reset cancels in-flight epoch; old request/ack cannot reappear as fresh; observed≠expected即失败 | 符合示例契约 |
| 20 / 8 bounded_channel_reports_overflow | `{"capacity":2,"undrained_frames":[1,2,3]}` | `["queued","queued","overflow_reported"]` | No silent overwrite or video backpressure; overflow is a counted whole-packet loss; observed≠expected即失败 | 符合示例契约 |
| 21 / 8 channel_atomic_order_and_loss_accounting | `{"drain":true}` | `[1,2,1]` | All admitted packets are whole and ordered, rejected packets are counted; observed≠expected即失败 | 符合示例契约 |
| 22 / 9 box_text_identity_mismatch | `{"box_frame":1,"text_frame":2}` | `"mixed_observation"` | Box/cross/text/count/state must represent one committed observation; observed≠expected即失败 | 符合示例契约 |
| 23 / 10 invalid_and_valid_absence_are_distinct | `{"after_confirmation":["invalid","no_target","no_target"]}` | `[["invalid",2,2,0,true],["no_target",3,0,1,true],["no_target",4,0,2,false]]` | Invalid frames do not count absence; valid absence advances loss policy; observed≠expected即失败 | 符合示例契约 |
| 24 / 10 silence_expires_old_observation | `{"last_positive":2,"now":8,"fixture_age_limit":5}` | `false` | Age advances with trusted time even without result strobes; observed≠expected即失败 | 符合示例契约 |
| 25 / 10 late_positive_cannot_refresh_age | `{"arrival":9,"capture":2,"fixture_age_limit":5}` | `["stale_result",2,0,0,false]` | Age derives from capture time, never packet arrival time; observed≠expected即失败 | 符合示例契约 |
| 26 / 10 future_timestamp_rejected | `{"now":1,"capture":3}` | `["future_time",0,0,0,false]` | Untrusted/future time cannot establish freshness; observed≠expected即失败 | 符合示例契约 |
| 27 / 10 age_budget_covers_entire_scan | `{"start":4,"duration_bound":2,"capture":0,"age_limit":5}` | `"age_budget"` | Frame-atomic display needs age margin through scan, not only at SOF; observed≠expected即失败 | 符合示例契约 |
| 28 / 3 reset_cancels_complete_tail_and_partial_frame | `{"frame1_eof":10,"due":15,"frame2_partial":true,"reset":13}` | `[[1,2],[]]` | Every reset-cancelled result is accounted, including complete pending tails; observed≠expected即失败 | 符合示例契约 |
| 29 / 10 age_inclusive_boundary_then_expiry | `{"last_capture":2,"age_limit":5,"now":[7,8]}` | `[true,false]` | Age equality is allowed; strictly greater expires without new packets; observed≠expected即失败 | 符合示例契约 |
| 30 / 10 invalid_train_expires_without_absence | `{"invalid_times":[3,4,5,6,7,8]}` | `["invalid",2,0,0,false]` | Invalid packets never count absence or refresh age; time still expires old target; observed≠expected即失败 | 符合示例契约 |
| 31 / 1 invalid_identity_cannot_be_replayed_valid | `{"same_frame":3,"validity":[false,true]}` | `[["invalid",0,0,0,false],["duplicate",0,0,0,false]]` | Every identity has one disposition including invalid; observed≠expected即失败 | 符合示例契约 |
| 32 / 8 distinct_clock_schedules_and_delayed_channel | `{"source_clock_period":4,"source_result_times":[0,8,16,24],"destination_clock_period":5,"destination_phase":3,"fixture_min_channel_delay":10,"capacity":3}` | `[[[13,1],[18,2],[28,3],[38,4]],0,0]` | Separate source/destination edges and bounded transport delay preserve atomic order; no physical CDC proof; observed≠expected即失败 | 符合示例契约 |
| 33 / 10 raw_wrapping_time_requires_unwrap | `{"reference_ticks":[10,0]}` | `"clock_moved_backwards"` | Common time must be monotonic/unwrapped; raw counter wrap cannot look fresh; observed≠expected即失败 | 符合示例契约 |
| 34 / 9 negative_wrong_box | `{"faulty_state":"wrong_box"}` | `"mixed_observation"` | Invariant rejects injected faulty committed state; observed≠expected即失败 | 符合示例契约 |
| 35 / 9 negative_wrong_text | `{"faulty_state":"wrong_text"}` | `"mixed_observation"` | Invariant rejects injected faulty committed state; observed≠expected即失败 | 符合示例契约 |
| 36 / 9 negative_wrong_session | `{"faulty_state":"wrong_session"}` | `"mixed_observation"` | Invariant rejects injected faulty committed state; observed≠expected即失败 | 符合示例契约 |

模型原始JSON还保存observed，便于逐项审查，不把模型视为硬件替身。
新增A2生产RTL或MAIN适配批准后，应将同一输入/期望移交真实RTL测试并保留失败；不允许只改期望来追求全PASS。
当前不存在真实相机→DDR→跨域→HDMI正确标注的闭环测试结果。
