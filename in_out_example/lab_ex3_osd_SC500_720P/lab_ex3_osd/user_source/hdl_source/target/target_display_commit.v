// Pixel-domain prepare/commit. The metadata packet is an atomic snapshot of
// the exact DDR read selection. Payload = FrameRef(162) + annotation(152).
// Annotation = box_session/frame(64), usable,state,class,count,bounds,center(88).
// This adapter never samples live guard output during a scan.
module target_display_commit #(
    parameter integer ENABLE=1,
    parameter [63:0] MAX_AGE_TICKS=64'd100000,
    parameter [63:0] MAX_SCAN_TICKS=64'd16501
)(
    input clk, rst_n, input [63:0] now_tick,
    input metadata_receive, input [505:0] metadata,
    input metadata_online, input scan_fault,
    input [23:0] video_rgb, input video_de, video_hs, video_vs,
    input blanking_start,
    output reg [23:0] out_rgb, output reg out_de,out_hs,out_vs,
    output wire [7:0] glyph_char, output wire [3:0] glyph_row,
    input [15:0] glyph_bits,
    output wire glyph_request,
    output reg display_enable,
    output reg [31:0] pixel_session,pixel_frame,
    output reg [1:0] pixel_slot, output reg [31:0] pixel_generation,
    output reg first_pixel,
    output reg [15:0] hidden_count,late_count
);
    reg [505:0] prepared;
    reg have_prepared, accepting, scan_started;
    reg [7:0] prepare_wait;
    reg [10:0] x;
    reg [9:0] y;
    reg de_d;
    reg [63:0] scan_start_tick;
    wire [1:0] slot=prepared[313:312];
    wire [31:0] generation=prepared[311:280];
    wire [31:0] session=prepared[279:248], frame=prepared[247:216];
    wire [63:0] captured=prepared[215:152];
    wire [31:0] box_session=prepared[151:120], box_frame=prepared[119:88];
    wire usable=prepared[87];
    wire [1:0] state=prepared[86:85];
    wire [19:0] count=prepared[82:63];
    wire [10:0] xmin=prepared[62:52],xmax=prepared[51:41],cx=prepared[40:30];
    wire [9:0] ymin=prepared[29:20],ymax=prepared[19:10],cy=prepared[9:0];
    wire first_now=video_de && !scan_started;
    // y increments on the preceding line's end; x resets on each DE fall.
    wire [10:0] px=x;
    wire [9:0] py=y;
    wire ready_annotation=ENABLE && metadata_online && !scan_fault && have_prepared &&
        prepare_wait>=8'd142 && usable && session==box_session && frame==box_frame &&
        now_tick>=captured && now_tick-captured<=MAX_AGE_TICKS-MAX_SCAN_TICKS;
    wire in_scan_budget=now_tick>=scan_start_tick && now_tick-scan_start_tick<=MAX_SCAN_TICKS;
    wire whole_mask=(first_now ? ready_annotation : display_enable) &&
        metadata_online && !scan_fault && (first_now || in_scan_budget);
    wire protected_region=(px<160 && py<160) ||
        (px>=375 && px<575 && py>=120 && py<144) ||
        (px>=800 && px<1248 && py>=16 && py<128);
    wire geometry_valid,text_valid;
    wire [23:0] geometry_rgb,text_rgb;
    wire [7:0] text_char;
    wire [3:0] text_row;
    wire diagnostic_region=video_de && px>=24 && px<888 && py>=680 && py<712;
    wire diagnostic_line=py>=696;
    wire [5:0] diagnostic_column=(px-24)>>4;
    reg [7:0] diagnostic_char;
    reg [31:0] diagnostic_number;
    reg [3:0] diagnostic_nibble;
    integer field_index,field_column;
    function [7:0] hexchar;
        input [3:0] n;
        begin hexchar=(n<10) ? 8'd48+n : 8'd55+n; end
    endfunction
    always @* begin
        diagnostic_char=8'd32; diagnostic_number=0; diagnostic_nibble=0;
        field_index=0; field_column=0;
        if(!diagnostic_line) begin
            case(diagnostic_column)
                0: diagnostic_char=metadata_online ? 8'h53 : 8'h21;
                10:diagnostic_char=8'h46;
                20:diagnostic_char=8'h47;
                30:diagnostic_char=8'h4c;
                31:diagnostic_char=hexchar({2'b0,slot});
                33:diagnostic_char=8'h44;
                39:diagnostic_char=8'h43;
                45:diagnostic_char=8'h51;
                default:begin
                    if(diagnostic_column>=1 && diagnostic_column<=8) begin
                        diagnostic_number=session; field_column=diagnostic_column-1;
                        diagnostic_char=hexchar(diagnostic_number>>(4*(7-field_column)));
                    end else if(diagnostic_column>=11 && diagnostic_column<=18) begin
                        diagnostic_number=frame; field_column=diagnostic_column-11;
                        diagnostic_char=hexchar(diagnostic_number>>(4*(7-field_column)));
                    end else if(diagnostic_column>=21 && diagnostic_column<=28) begin
                        diagnostic_number=generation; field_column=diagnostic_column-21;
                        diagnostic_char=hexchar(diagnostic_number>>(4*(7-field_column)));
                    end else if(diagnostic_column>=34 && diagnostic_column<=37) begin
                        diagnostic_number=prepared[361:346]; field_column=diagnostic_column-34;
                        diagnostic_char=hexchar(diagnostic_number>>(4*(3-field_column)));
                    end else if(diagnostic_column>=40 && diagnostic_column<=43) begin
                        diagnostic_number=prepared[345:330]; field_column=diagnostic_column-40;
                        diagnostic_char=hexchar(diagnostic_number>>(4*(3-field_column)));
                    end else if(diagnostic_column>=46 && diagnostic_column<=49) begin
                        diagnostic_number=prepared[329:314]; field_column=diagnostic_column-46;
                        diagnostic_char=hexchar(diagnostic_number>>(4*(3-field_column)));
                    end
                end
            endcase
        end else begin
            // Nine fields: duplicate/reorder/wrong-session/identity/invalid/
            // cancelled/stale/time/timeout. Literal labels documented in handoff.
            field_index=diagnostic_column/6; field_column=diagnostic_column%6;
            if(field_index<9) begin
                if(field_column==0) begin
                    case(field_index)
                        0:diagnostic_char=8'h44; 1:diagnostic_char=8'h52; 2:diagnostic_char=8'h57;
                        3:diagnostic_char=8'h49; 4:diagnostic_char=8'h56; 5:diagnostic_char=8'h43;
                        6:diagnostic_char=8'h53; 7:diagnostic_char=8'h54; 8:diagnostic_char=8'h4f;
                    endcase
                end else if(field_column<5) begin
                    diagnostic_number=(prepared[505:362]>>((8-field_index)*16)) & 16'hffff;
                    diagnostic_char=hexchar(diagnostic_number>>(4*(4-field_column)));
                end
            end
        end
    end
    assign glyph_char=diagnostic_region ? diagnostic_char : text_char;
    assign glyph_row=diagnostic_region ? (py-680)&15 : text_row;
    color_target_overlay u_box(
        .I_pixel_valid(video_de),.I_x(px),.I_y(py),
        .I_result_valid(1'b1),.I_target_present(1'b1),
        .I_xmin(xmin),.I_xmax(xmax),.I_ymin(ymin),.I_ymax(ymax),
        .I_center_x(cx),.I_center_y(cy),.O_overlay_valid(geometry_valid),.O_overlay_rgb(geometry_rgb));
    color_target_text_overlay #(.X0(24),.Y0(640)) u_text(
        .clk(clk),.rst_n(rst_n),.I_pixel_valid(video_de),.I_x(px),.I_y(py),
        .I_update(1'b0),.I_show(usable),.I_state(state),.I_count(count),
        .I_center_x(cx),.I_center_y(cy),.O_glyph_char(text_char),.O_glyph_row(text_row),
        .I_glyph_bits(glyph_bits),.O_overlay_valid(text_valid),.O_overlay_rgb(text_rgb));
    assign glyph_request=(video_de && py>=640 && py<674 && px>=24 && px<248) || diagnostic_region;
    always @(posedge clk or negedge rst_n) begin
        if(!rst_n) begin
            prepared<=0; have_prepared<=0; prepare_wait<=0;
            accepting<=0; scan_started<=0; x<=0; y<=0; de_d<=0;
            scan_start_tick<=0; display_enable<=0;
            out_rgb<=0; out_de<=0; out_hs<=0; out_vs<=0;
            pixel_session<=0; pixel_frame<=0; pixel_slot<=0; pixel_generation<=0;
            first_pixel<=0; hidden_count<=0; late_count<=0;
        end else begin
            out_de<=video_de; out_hs<=video_hs; out_vs<=video_vs;
            de_d<=video_de; first_pixel<=first_now;
            if(blanking_start) begin
                accepting<=1; have_prepared<=0; prepare_wait<=0;
                scan_started<=0; display_enable<=0; x<=0; y<=0;
            end
            if(metadata_receive) begin
                if(accepting && !video_de && !scan_started) begin
                    prepared<=metadata; have_prepared<=1; prepare_wait<=0;
                end else if(!(&late_count)) late_count<=late_count+1'b1;
            end else if(have_prepared && prepare_wait<142) prepare_wait<=prepare_wait+1'b1;
            if(first_now) begin
                accepting<=0; scan_started<=1; scan_start_tick<=now_tick;
                display_enable<=ready_annotation;
                pixel_session<=session; pixel_frame<=frame; pixel_slot<=slot; pixel_generation<=generation;
                if(!ready_annotation && !(&hidden_count)) hidden_count<=hidden_count+1'b1;
            end
            if(video_de) x<=x+1'b1;
            if(de_d && !video_de) begin x<=0; y<=y+1'b1; end
            if(!metadata_online || scan_fault || (scan_started && !in_scan_budget)) display_enable<=0;
            if(ENABLE && have_prepared && diagnostic_region) out_rgb<=glyph_bits[15-((px-24)&15)] ? 24'hfff200 : 24'h101010;
            else if(video_de && whole_mask && !protected_region && text_valid) out_rgb<=text_rgb;
            else if(video_de && whole_mask && !protected_region && geometry_valid) out_rgb<=geometry_rgb;
            else out_rgb<=video_rgb;
        end
    end
endmodule
