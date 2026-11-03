`timescale 1ns / 1ps
// color_target_track —— TARGET 的动态跟踪状态机与防抖（T4）。
//
// 对应协议 §2.2 T4："完成目标移动、目标消失与重现时的状态更新和适度防抖，支持可重复的
// 动态跟踪演示。"
//
// 它接在 color_target_detect 之后、color_target_overlay 之前，把"每帧一次的原始检出"
// 变成"稳定可演示的显示结果"：
//   检出 → track → overlay
//
// 状态机（每个 strobe 评估一帧）：
//   S_SEARCH(0) 无目标
//   S_ACQ(1)    连续检出中，但还没到 ACQ_FRAMES
//   S_TRACK(2)  已确认，框随检出更新
//   S_HOLD(3)   原在 TRACK，本帧丢失但未达 LOST_FRAMES —— **保持上一次的框**
//   跳变：SEARCH/ACQ --连续 ACQ_FRAMES 帧检出--> TRACK
//         TRACK --丢失--> HOLD --连续 LOST_FRAMES 帧丢失--> SEARCH
//         HOLD  --检出--> TRACK（目标重现）
//
// 三点刻意的设计：
//   1. **中止帧不改变状态**（I_result_valid=0）。协议 §4.3 说"检测模块丢弃该帧结果"，
//      但丢掉一帧结果不等于"目标消失"——把中止帧当丢失会误判。所以直接跳过不评估。
//   2. **会话变化强制清零**。协议 §4.1：复位/重新采集开始新 session，不得把旧会话的
//      跟踪状态带进新会话。这里把新会话的第一帧当作 SEARCH 重新判定，而不是丢弃它。
//   3. **跳变门限默认关闭**。MAX_JUMP=0 表示不启用；启用后本帧检出若与上次接受的中心
//      相差超过 MAX_JUMP 像素，则当作未检出。它是给"画面里有第二块同色区域"准备的，
//      但会让快速移动的目标被判丢，**默认不启用**，需按实测场景再决定。
//
// 参数合法范围（都在编译期夹取，不产生运行时逻辑，也避免越界参数造成的退化行为）：
//   ACQ_FRAMES / LOST_FRAMES  1..255 —— 底层是 8 位计数器。取 0 与取 1 同义（都表示
//                             "立即"，即不需要防抖）；超过 255 在 8 位里无法表示，
//                             一律夹到 255，而不是让高位被悄悄丢掉。
//   MAX_JUMP                  0..    —— 0 表示关闭；负数夹到 0（否则"任意偏移都算超标"
//                             会把目标永久锁死在 HOLD）。
module color_target_track #(
    parameter integer XW          = 11,
    parameter integer YW          = 10,
    parameter integer ACQ_FRAMES  = 3,    // 连续检出多少帧才算确认（1..255）
    parameter integer LOST_FRAMES = 15,   // 连续丢失多少帧才算彻底失去（1..255）
    parameter integer MAX_JUMP    = 0     // 0 = 关闭跳变门限；单位像素
)(
    input               clk,
    input               rst_n,

    // ---- 来自 color_target_detect 的整帧结果 ----
    input               I_result_strobe,   // 接 detect 的 O_result_ready
    input               I_result_valid,    // detect 的 O_result_valid
    input               I_target_present,
    input      [19:0]   I_pixel_count,
    input      [XW-1:0] I_xmin, I_xmax, I_center_x,
    input      [YW-1:0] I_ymin, I_ymax, I_center_y,
    input      [31:0]   I_session_id, I_frame_id,

    // ---- 供 overlay 与 OSD 使用的稳定结果 ----
    output reg [1:0]    O_track_state,     // 0=SEARCH 1=ACQ 2=TRACK 3=HOLD
    output reg          O_show,            // 1 时有可显示的框（TRACK 或 HOLD）
    output reg [19:0]   O_out_count,
    output reg [XW-1:0] O_out_xmin, O_out_xmax, O_out_center_x,
    output reg [YW-1:0] O_out_ymin, O_out_ymax, O_out_center_y,
    output reg [31:0]   O_out_session_id, O_out_frame_id,
    output reg          O_state_change     // 状态发生变化时的一拍脉冲
);
    localparam [1:0] S_SEARCH = 2'd0, S_ACQ = 2'd1, S_TRACK = 2'd2, S_HOLD = 2'd3;

    // 计数器是 8 位，参数在这里夹到可表示范围（编译期常量折叠，无运行时逻辑）：
    //   0 → 1：与"立即确认/立即隐藏"同义，不是"永不"。取 0 会让阈值判断退化成
    //          "(0+1) >= 0" 恒真，表面上也是立即，但语义含糊且 0 帧防抖本身就是陷阱。
    //   >255 → 255：不夹的话 (eff + 1) >= (参数) 里参数的高位会被 [7:0] 截掉，
    //          例如 ACQ_FRAMES=256 截成 0，第一帧就确认，和"要 256 帧"完全相反。
    localparam integer ACQ_EFF  = (ACQ_FRAMES  < 1) ? 1 : ((ACQ_FRAMES  > 255) ? 255 : ACQ_FRAMES);
    localparam integer LOST_EFF = (LOST_FRAMES < 1) ? 1 : ((LOST_FRAMES > 255) ? 255 : LOST_FRAMES);
    // 负数夹到 0（= 关闭）：否则"任意偏移都超过门限"会让目标一旦确认就再也接受不到更新
    localparam integer MAX_JUMP_EFF = (MAX_JUMP < 0) ? 0 : MAX_JUMP;

    reg [1:0]  state;
    reg [7:0]  acq_cnt, lost_cnt;
    reg [XW-1:0] last_cx;
    reg [YW-1:0] last_cy;
    reg [31:0] cur_session;

    wire strobe = I_result_strobe && I_result_valid;
    wire session_new = (I_session_id != cur_session);

    // 新会话一律按"未开始跟踪"评估本帧，而不是把它丢掉
    wire [1:0] eff_state = session_new ? S_SEARCH : state;
    wire [7:0] eff_acq   = session_new ? 8'd0     : acq_cnt;
    wire [7:0] eff_lost  = session_new ? 8'd0     : lost_cnt;
    wire eff_tracked = (eff_state == S_TRACK) || (eff_state == S_HOLD);

    // 跳变门限（默认关闭）
    wire [XW:0] ddx = (I_center_x >= last_cx) ? (I_center_x - last_cx) : (last_cx - I_center_x);
    wire [YW:0] ddy = (I_center_y >= last_cy) ? (I_center_y - last_cy) : (last_cy - I_center_y);
    wire jump_bad = (MAX_JUMP_EFF != 0) && eff_tracked &&
                    ((ddx > MAX_JUMP_EFF) || (ddy > MAX_JUMP_EFF));

    wire accept = strobe && I_target_present && !jump_bad;
    wire miss   = strobe && !accept;

    // ---- 组合的下一状态 ----
    reg [1:0] nxt_state;
    reg [7:0] nxt_acq, nxt_lost;
    always @* begin
        nxt_state = eff_state;
        nxt_acq   = eff_acq;
        nxt_lost  = eff_lost;
        if (strobe) begin
            if (accept) begin
                nxt_acq  = eff_acq + 8'd1;
                nxt_lost = 8'd0;
                if (eff_state == S_SEARCH || eff_state == S_ACQ)
                    nxt_state = ((eff_acq + 8'd1) >= ACQ_EFF[7:0]) ? S_TRACK : S_ACQ;
                else
                    nxt_state = S_TRACK;              // TRACK 保持；HOLD 表示目标重现
            end else begin
                nxt_acq = 8'd0;
                case (eff_state)
                    S_SEARCH: nxt_state = S_SEARCH;
                    S_ACQ:    nxt_state = S_SEARCH;   // 还没确认就断了，退回搜索
                    S_TRACK:  begin
                        // 门限对"TRACK 的首次丢失"同样生效：LOST_FRAMES=1 时必须立刻隐藏，
                        // 而不是先进 HOLD 再等下一次丢失（原实现漏了这一步，与 S_HOLD 分支不一致）。
                        nxt_lost  = 8'd1;
                        nxt_state = (8'd1 >= LOST_EFF[7:0]) ? S_SEARCH : S_HOLD;
                    end
                    default:  begin                   // S_HOLD
                        nxt_lost  = eff_lost + 8'd1;
                        nxt_state = ((eff_lost + 8'd1) >= LOST_EFF[7:0]) ? S_SEARCH : S_HOLD;
                    end
                endcase
            end
        end
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= S_SEARCH; acq_cnt <= 8'd0; lost_cnt <= 8'd0;
            last_cx <= {XW{1'b0}}; last_cy <= {YW{1'b0}}; cur_session <= 32'd0;
            O_track_state <= S_SEARCH; O_show <= 1'b0; O_state_change <= 1'b0;
            O_out_count <= 20'd0;
            O_out_xmin <= {XW{1'b0}}; O_out_xmax <= {XW{1'b0}}; O_out_center_x <= {XW{1'b0}};
            O_out_ymin <= {YW{1'b0}}; O_out_ymax <= {YW{1'b0}}; O_out_center_y <= {YW{1'b0}};
            O_out_session_id <= 32'd0; O_out_frame_id <= 32'd0;
        end else begin
            if (strobe) begin
                state    <= nxt_state;
                acq_cnt  <= nxt_acq;
                lost_cnt <= nxt_lost;
                cur_session <= I_session_id;
                if (accept) begin
                    last_cx <= I_center_x; last_cy <= I_center_y;
                    // 只接受时更新显示结果；HOLD 期间保持上一次的值不动
                    O_out_count     <= I_pixel_count;
                    O_out_xmin      <= I_xmin;      O_out_xmax   <= I_xmax;
                    O_out_ymin      <= I_ymin;      O_out_ymax   <= I_ymax;
                    O_out_center_x  <= I_center_x;  O_out_center_y <= I_center_y;
                    O_out_session_id<= I_session_id;O_out_frame_id <= I_frame_id;
                end
                O_track_state  <= nxt_state;
                O_show         <= (nxt_state == S_TRACK) || (nxt_state == S_HOLD);
                O_state_change <= (nxt_state != eff_state);
            end else begin
                O_state_change <= 1'b0;
            end
        end
    end
endmodule
