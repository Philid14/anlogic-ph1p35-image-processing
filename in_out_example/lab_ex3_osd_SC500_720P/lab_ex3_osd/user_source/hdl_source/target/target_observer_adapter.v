// Read-only normalization at the existing AWB boundary. RAW SOF is the actual
// decoded first-valid pixel, never the early AWB notification. Metadata is held
// across the ISP; an overlapping acquisition poisons the old transaction.
// The caller supplies the common-clock timestamp snapshot and session issuer.
module target_observer_adapter #(
    parameter integer WIDTH=1280, HEIGHT=720
)(
    input clk, input rst_n,
    input [31:0] control_session, input session_ready,
    input [63:0] now_tick, input time_valid,
    input raw_valid, raw_sof, raw_eol, native_frame_end,
    input awb_user, awb_valid, awb_last, input [95:0] awb_rgb,
    input external_error,
    output reg capture_start,
    output reg [31:0] capture_session, capture_frame,
    output reg [63:0] capture_time,
    output wire pixel_valid, output wire [95:0] pixel_rgb,
    output wire sof, eol, eof,
    output reg [10:0] x0, output reg [9:0] y,
    output reg [31:0] observation_session, observation_frame,
    output reg [63:0] observation_time,
    output wire frame_abort,
    output reg raw_complete, raw_good,
    output reg observer_done, observer_good,
    output reg epoch_fault,
    output reg [15:0] raw_error_count, observer_error_count
);
    localparam integer BEATS=(WIDTH/4)*HEIGHT;
    reg [31:0] issued_frame, issued_session;
    reg raw_open, raw_bad, identity_valid;
    reg [17:0] raw_beats;
    reg [10:0] raw_x;
    reg [9:0] raw_y;
    reg obs_armed, obs_bad, obs_finished;
    reg [17:0] obs_beats;
    reg [31:0] last_observed_frame, last_observed_session;
    reg have_observed;
    wire raw_first=raw_sof && raw_valid;
    wire bad_raw_geometry=raw_eol!=(raw_x==WIDTH-4);
    wire bad_obs_geometry=awb_last!=(x0==WIDTH-4);
    assign pixel_valid=awb_valid && obs_armed && !obs_finished;
    assign pixel_rgb=awb_rgb; // No pixel reordering or numerical conversion.
    assign sof=pixel_valid && obs_beats==0;
    assign eol=pixel_valid && x0==WIDTH-4;
    assign eof=eol && y==HEIGHT-1;
    assign frame_abort=obs_bad || external_error || raw_bad ||
        (pixel_valid && bad_obs_geometry);
    function [15:0] inc;
        input [15:0] v;
        begin inc=(&v) ? v : v+1'b1; end
    endfunction
    always @(posedge clk or negedge rst_n) begin
        if(!rst_n) begin
            capture_start<=0; capture_session<=0; capture_frame<=0; capture_time<=0;
            issued_frame<=0; issued_session<=0; identity_valid<=0;
            raw_open<=0; raw_bad<=0; raw_beats<=0; raw_x<=0; raw_y<=0;
            raw_complete<=0; raw_good<=0;
            obs_armed<=0; obs_bad<=0; obs_finished<=0; obs_beats<=0;
            x0<=0; y<=0; observation_session<=0; observation_frame<=0; observation_time<=0;
            observer_done<=0; observer_good<=0; epoch_fault<=0;
            have_observed<=0; last_observed_frame<=0; last_observed_session<=0;
            raw_error_count<=0; observer_error_count<=0;
        end else begin
            capture_start<=0; raw_complete<=0; observer_done<=0;
            if(!session_ready || !time_valid) begin
                identity_valid<=0; obs_bad<=1;
            end
            if(external_error) begin raw_bad<=1; obs_bad<=1; end
            if(raw_first) begin
                if(raw_open || (obs_armed && !obs_finished)) begin
                    epoch_fault<=1; obs_bad<=1;
                end
                if(issued_session!=control_session) begin
                    issued_session<=control_session; issued_frame<=0;
                    capture_frame<=0;
                end else begin
                    issued_frame<=issued_frame+1'b1; capture_frame<=issued_frame+1'b1;
                end
                capture_session<=control_session; capture_time<=now_tick;
                capture_start<=session_ready && time_valid;
                identity_valid<=session_ready && time_valid && !epoch_fault &&
                    !(issued_session==control_session && issued_frame>=32'hfffffffd);
                if(issued_session==control_session && issued_frame>=32'hfffffffd) epoch_fault<=1;
                raw_open<=1; raw_bad<=external_error || raw_eol!=(WIDTH==4);
                raw_beats<=1; raw_x<=(WIDTH==4) ? 0 : 4;
                raw_y<=(WIDTH==4) ? 1 : 0;
            end else if(raw_valid) begin
                if(!raw_open || raw_beats>=BEATS || bad_raw_geometry) raw_bad<=1;
                if(raw_beats<BEATS+1) raw_beats<=raw_beats+1'b1;
                raw_x<=(raw_x==WIDTH-4) ? 0 : raw_x+4;
                if(raw_x==WIDTH-4) raw_y<=raw_y+1'b1;
            end
            if(native_frame_end) begin
                raw_open<=0; raw_complete<=1;
                raw_good<=raw_open && !raw_bad && !external_error &&
                    raw_beats+raw_valid==BEATS && (!raw_valid || !bad_raw_geometry);
                if(!raw_open || raw_bad || external_error || raw_beats+raw_valid!=BEATS)
                    raw_error_count<=inc(raw_error_count);
            end
            if(awb_user) begin
                // AWB early user must precede first RGB, as required by the
                // frozen ISP. A collision is invalidated rather than guessed.
                obs_armed<=1; obs_finished<=0; obs_beats<=0; x0<=0; y<=0;
                observation_session<=capture_session; observation_frame<=capture_frame;
                observation_time<=capture_time;
                obs_bad<=!identity_valid || awb_valid || external_error ||
                    (have_observed && capture_session==last_observed_session &&
                     capture_frame<=last_observed_frame);
                have_observed<=1;
                last_observed_session<=capture_session; last_observed_frame<=capture_frame;
                if(obs_armed && !obs_finished) epoch_fault<=1;
            end else if(awb_valid) begin
                if(!obs_armed || obs_finished || bad_obs_geometry) begin
                    obs_bad<=1;
                    if(!obs_finished) observer_error_count<=inc(observer_error_count);
                end
                if(pixel_valid) begin
                    obs_beats<=obs_beats+1'b1;
                    x0<=eol ? 0 : x0+4;
                    if(eol) y<=y+1'b1;
                    if(eof) begin
                        obs_finished<=1; observer_done<=1;
                        observer_good<=!frame_abort && obs_beats==BEATS-1;
                    end
                end
            end else if(awb_last) begin
                obs_bad<=1; observer_error_count<=inc(observer_error_count);
            end
        end
    end
endmodule
