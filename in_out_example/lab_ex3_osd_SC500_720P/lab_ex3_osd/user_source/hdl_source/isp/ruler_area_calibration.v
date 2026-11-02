// Centimeter coarse scale: same twelve-row cache / wide search / frame checks.
// At least five thin marks per row. Average adjacent 10mm intervals, then
// agree two adjacent rows; search ALL bands and prefer the larger stable
// pitch to avoid accepting the 5mm line band before the 10mm tips appear.
// Operator supplies a horizontal METRIC ruler on a clean light background.
// Not OCR: a different regularly spaced pattern can be mistaken for ticks.
module ruler_area_calibration #(
    parameter WIDTH=1280,HEIGHT=720,X0=256,Y0=192,SCAN_PIXELS=768,SEARCH_HEIGHT=288
)(input clk,rst_n,input [31:0] gray,input valid,user,last,
  input enable,request_toggle,output reg [10:0] span,
  output reg calibrated,output reg [2:0] status);
    localparam WORDS=SCAN_PIXELS/4;
    reg [31:0] memory[0:12*WORDS-1];
    reg [10:0] band_y;reg search_contrast;
    reg [7:0] lows[0:11],highs[0:11];
    reg [10:0] x,y;wire [10:0] px=user?0:x,py=user?0:y;
    reg pending,capturing,seen,armed,bad,finished;
    reg [17:0] beats;
    wire geometry=last!=(px==WIDTH-4);
    wire complete=armed && finished && !bad && beats==(WIDTH/4)*HEIGHT;
    reg sample_line;reg [3:0] capture_line;
    reg [7:0] beat_low,beat_high;integer k;
    always @*begin
        sample_line=0;capture_line=0;beat_low=255;beat_high=0;
        for(k=0;k<12;k=k+1)if(py==band_y+k && py<Y0+SEARCH_HEIGHT)begin sample_line=1;capture_line=k;end
        for(k=0;k<4;k=k+1)begin
            if(gray[31-k*8-:8]<beat_low)beat_low=gray[31-k*8-:8];
            if(gray[31-k*8-:8]>beat_high)beat_high=gray[31-k*8-:8];
        end
    end
    wire [11:0] write_address=capture_line*WORDS+((px-X0)>>2);
    always @(posedge clk)
        if(capturing && enable && valid && !user && sample_line && px>=X0 && px<X0+SCAN_PIXELS)
            memory[write_address]<=gray;

    localparam IDLE=0,SETUP=1,FETCH=2,WAIT_READ=3,PIXEL=4,DIVIDE=5,NEXT_LINE=6,FINISH=7,ROW_END=8;
    reg [3:0] state;reg [11:0] address;reg [31:0] word;
    always @(posedge clk)word<=memory[address];
    reg [3:0] line_no;reg [1:0] lane;reg [9:0] pos,start;
    reg in_tick,have_center,any_contrast,have_anchor;
    reg [10:0] run_width,last_center,seed_gap,run_sum,best_sum;
    reg [6:0] run_n,best_n;reg [10:0] anchor,global_best;
    reg [7:0] cut;
    wire [10:0] center={1'b0,start}+{1'b0,pos}-1'b1;
    wire [10:0] gap=center-last_center;
    wire [10:0] gap_error=gap>=seed_gap?gap-seed_gap:seed_gap-gap;
    wire similar=run_n!=0 && gap_error<=((seed_gap>>2)+2);
    wire [6:0] next_n=similar?run_n+1'b1:7'd1;
    wire [10:0] next_sum=similar?run_sum+gap:gap;
    reg [16:0] dividend,quotient;reg [9:0] remainder;
    reg [8:0] denominator;reg [4:0] step;
    wire [10:0] trial={remainder,dividend[16]};
    wire qbit=trial>={2'b0,denominator};wire [16:0] qnext={quotient[15:0],qbit};
    wire [16:0] difference=qnext>=anchor?qnext-anchor:anchor-qnext;
    wire [17:0] mean_span=({1'b0,qnext}+{7'd0,anchor}+1'b1)>>1;
    integer j;
    always @(posedge clk or negedge rst_n)begin
        if(!rst_n)begin
            band_y<=Y0;search_contrast<=0;
            x<=0;y<=0;pending<=0;capturing<=0;seen<=0;armed<=0;bad<=0;finished<=0;beats<=0;
            span<=0;calibrated<=0;status<=0;state<=IDLE;address<=0;line_no<=0;lane<=0;pos<=0;start<=0;
            in_tick<=0;have_center<=0;any_contrast<=0;have_anchor<=0;anchor<=0;global_best<=0;
            run_width<=0;last_center<=0;seed_gap<=0;run_sum<=0;best_sum<=0;run_n<=0;best_n<=0;
            cut<=0;dividend<=0;quotient<=0;remainder<=0;denominator<=1;step<=0;
            for(j=0;j<12;j=j+1)begin lows[j]<=255;highs[j]<=0;end
        end else begin
            seen<=request_toggle;
            if(user)begin
                x<=valid?4:0;y<=0;armed<=1;bad<=valid && geometry;beats<=valid?1:0;finished<=0;
            end else if(valid)begin
                if(!armed || finished || geometry)bad<=1;
                if(beats<(WIDTH/4)*HEIGHT+1)beats<=beats+1'b1;
                x<=px==WIDTH-4?0:px+4;
                if(px==WIDTH-4)begin y<=py+1'b1;if(py==HEIGHT-1)finished<=1;end
            end else if(last)bad<=1;
            if(capturing && valid && sample_line && px>=X0 && px<X0+SCAN_PIXELS)begin
                if(beat_low<lows[capture_line])lows[capture_line]<=beat_low;
                if(beat_high>highs[capture_line])highs[capture_line]<=beat_high;
            end
            if(!enable)begin
                if(pending || capturing || state!=IDLE)status<=7;
                pending<=0;capturing<=0;state<=IDLE;
            end else if(request_toggle!=seen)begin
                pending<=1;capturing<=0;calibrated<=0;status<=1;state<=IDLE;
                band_y<=Y0;search_contrast<=0;global_best<=0;have_anchor<=0;
            end else begin
                if(user && pending)begin
                    pending<=0;capturing<=1;
                    for(j=0;j<12;j=j+1)begin lows[j]<=255;highs[j]<=0;end
                end
                if(user && capturing)begin
                    capturing<=0;
                    if(!complete)begin status<=6;state<=IDLE;global_best<=0;end
                    else begin status<=2;state<=SETUP;line_no<=0;any_contrast<=0;have_anchor<=0;end
                end
                case(state)
                    SETUP:begin
                        if(highs[line_no]<lows[line_no] || ({1'b0,highs[line_no]}-{1'b0,lows[line_no]})<16)begin
                            have_anchor<=0;state<=NEXT_LINE;
                        end else begin
                            any_contrast<=1;
                            cut<=lows[line_no]+(({1'b0,highs[line_no]}-{1'b0,lows[line_no]})>>2);
                            address<=line_no*WORDS;pos<=0;lane<=0;in_tick<=0;have_center<=0;
                            run_width<=0;seed_gap<=0;run_n<=0;run_sum<=0;best_n<=0;best_sum<=0;state<=FETCH;
                        end
                    end
                    FETCH:state<=WAIT_READ;
                    WAIT_READ:state<=PIXEL;
                    PIXEL:begin
                        if(word[31-lane*8-:8]<cut)begin
                            if(!in_tick)begin start<=pos;run_width<=1;in_tick<=1;end
                            else if(run_width<SCAN_PIXELS)run_width<=run_width+1'b1;
                        end else if(in_tick)begin
                            in_tick<=0;
                            if(start!=0 && run_width<=4)begin
                                have_center<=1;last_center<=center;
                                if(have_center && gap>=24 && gap<=240)begin
                                    if(!similar)seed_gap<=gap;
                                    run_n<=next_n;run_sum<=next_sum;
                                    if(next_n>=4 && next_sum>best_sum)begin best_n<=next_n;best_sum<=next_sum;end
                                end else begin run_n<=0;run_sum<=0;end
                            end else begin have_center<=0;run_n<=0;run_sum<=0;end
                        end
                        if(pos==SCAN_PIXELS-1)state<=ROW_END;
                        else begin
                            pos<=pos+1'b1;lane<=lane+1'b1;
                            if(lane==3)begin address<=address+1'b1;state<=FETCH;end
                        end
                    end
                    ROW_END:begin
                        if(best_n>=4)begin
                            // doubled pixel separation * 5 / intervals = px per100mm.
                            dividend<={6'd0,best_sum}*17'd5+(best_n>>1);denominator<={2'd0,best_n};
                            quotient<=0;remainder<=0;step<=0;state<=DIVIDE;
                        end else begin have_anchor<=0;state<=NEXT_LINE;end
                    end
                    DIVIDE:begin
                        dividend<={dividend[15:0],1'b0};quotient<=qnext;
                        remainder<=qbit?trial-{2'b0,denominator}:trial;
                        if(step==16)begin
                            if(qnext>=120 && qnext<=1200)begin
                                if(have_anchor && difference<=((anchor>>3)+12) && mean_span>global_best)
                                    global_best<=mean_span[10:0];
                                anchor<=qnext[10:0];have_anchor<=1;
                            end else have_anchor<=0;
                            state<=NEXT_LINE;
                        end else step<=step+1'b1;
                    end
                    NEXT_LINE:begin
                        if(line_no==11)state<=FINISH;
                        else begin line_no<=line_no+1'b1;state<=SETUP;end
                    end
                    FINISH:begin
                        state<=IDLE;search_contrast<=search_contrast || any_contrast;
                        if(band_y+11<Y0+SEARCH_HEIGHT-1)begin band_y<=band_y+11;pending<=1;status<=2;end
                        else if(global_best!=0)begin span<=global_best;calibrated<=1;status<=3;end
                        else status<=(search_contrast || any_contrast)?5:4;
                    end
                endcase
            end
        end
    end
endmodule
