// One-frame horizontal 1mm ruler reader: six heights, per-line contrast,
// dominant inter-tick intervals, two agreeing accepted line estimates.
// Known metric ticks are an operator precondition, not OCR/unit recognition.
module ruler_robust_calibration #(
    parameter WIDTH=1280,HEIGHT=720,X0=384,Y0=288,LINE_STEP=6
)(input clk,rst_n,input [31:0] gray,input valid,user,last,
  input enable,request_toggle,output reg [10:0] span,
  output reg calibrated,output reg [2:0] status);
    reg [31:0] memory[0:767];
    reg [7:0] lows[0:5],highs[0:5];
    reg [10:0] x,y;wire [10:0] px=user?0:x,py=user?0:y;
    reg pending,capturing,seen,armed,bad,finished;
    reg [17:0] beats;
    wire geometry=last!=(px==WIDTH-4);
    wire complete=armed && finished && !bad && beats==(WIDTH/4)*HEIGHT;
    reg sample_line;reg [2:0] capture_line;
    reg [7:0] beat_low,beat_high;integer k;
    always @*begin
        sample_line=0;capture_line=0;beat_low=255;beat_high=0;
        for(k=0;k<6;k=k+1)if(py==Y0+k*LINE_STEP)begin sample_line=1;capture_line=k;end
        for(k=0;k<4;k=k+1)begin
            if(gray[31-k*8-:8]<beat_low)beat_low=gray[31-k*8-:8];
            if(gray[31-k*8-:8]>beat_high)beat_high=gray[31-k*8-:8];
        end
    end
    wire [9:0] write_address={capture_line,7'b0}+((px-X0)>>2);
    always @(posedge clk)
        if(capturing && enable && valid && !user && sample_line && px>=X0 && px<X0+512)
            memory[write_address]<=gray;
    localparam IDLE=0,SETUP=1,CLEAR=2,FETCH=3,WAIT_READ=4,PIXEL=5,SCAN=6,RATIO=7,DIVIDE=8;
    reg [3:0] state;reg [9:0] address;reg [31:0] word;
    always @(posedge clk)word<=memory[address];
    reg [2:0] line_no;reg [1:0] lane;reg [8:0] pos,start;
    reg in_tick,have_center,any_contrast,have_anchor;
    reg [9:0] run_width,last_center;reg [10:0] anchor;
    reg [7:0] cut,eligible;
    wire [9:0] center={1'b0,start}+{1'b0,pos}-1'b1;
    wire [9:0] gap=center-last_center;
    wire ended=state==PIXEL && in_tick && word[31-lane*8-:8]>=cut;
    wire add_gap=ended && start!=0 && run_width<=8 && have_center && gap>=4 && gap<=32;
    // A small distributed scratch RAM, cleared serially, not reset as 256 FF.
    reg [7:0] histogram[0:31];reg [5:0] scan_index;reg [4:0] clear_index;
    wire [4:0] hist_address=state==CLEAR?clear_index:state==PIXEL?(gap-4):scan_index[4:0];
    wire [7:0] hist_read=histogram[hist_address];
    always @(posedge clk)begin
        if(state==CLEAR)histogram[hist_address]<=0;
        else if(add_gap)histogram[hist_address]<=hist_read+1'b1;
    end
    reg [7:0] delay0,delay1,delay2,delay3,delay4;
    reg [8:0] window_count,best_count;
    reg [15:0] window_weight,best_weight;
    wire [7:0] incoming=scan_index<=28?hist_read:0;
    wire [15:0] incoming_weight=incoming*(scan_index+6'd4);
    wire [15:0] outgoing_weight=delay4*(scan_index-6'd1);
    wire [8:0] count_next=window_count+{1'b0,incoming}-{1'b0,delay4};
    wire [15:0] weight_next=window_weight+incoming_weight-outgoing_weight;
    reg [15:0] dividend,quotient;reg [8:0] remainder;
    reg [7:0] denominator;reg [4:0] step;
    wire [9:0] trial={remainder,dividend[15]};
    wire qbit=trial>={2'b0,denominator};wire [15:0] qnext={quotient[14:0],qbit};
    wire [15:0] difference=qnext>=anchor?qnext-anchor:anchor-qnext;
    integer j;
    task advance_line;
        begin
            if(line_no==5)begin state<=IDLE;status<=any_contrast?5:4;end
            else begin line_no<=line_no+1'b1;state<=SETUP;end
        end
    endtask
    always @(posedge clk or negedge rst_n)begin
        if(!rst_n)begin
            x<=0;y<=0;pending<=0;capturing<=0;seen<=0;armed<=0;bad<=0;finished<=0;beats<=0;
            span<=0;calibrated<=0;status<=0;state<=IDLE;address<=0;line_no<=0;lane<=0;pos<=0;start<=0;
            in_tick<=0;have_center<=0;any_contrast<=0;have_anchor<=0;anchor<=0;run_width<=0;last_center<=0;
            cut<=0;eligible<=0;scan_index<=0;clear_index<=0;
            delay0<=0;delay1<=0;delay2<=0;delay3<=0;delay4<=0;
            window_count<=0;best_count<=0;window_weight<=0;best_weight<=0;
            dividend<=0;quotient<=0;remainder<=0;denominator<=1;step<=0;
            for(j=0;j<6;j=j+1)begin lows[j]<=255;highs[j]<=0;end
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
            if(capturing && valid && sample_line && px>=X0 && px<X0+512)begin
                if(beat_low<lows[capture_line])lows[capture_line]<=beat_low;
                if(beat_high>highs[capture_line])highs[capture_line]<=beat_high;
            end
            if(!enable)begin
                if(pending || capturing || state!=IDLE)status<=7;
                pending<=0;capturing<=0;state<=IDLE;
            end else if(request_toggle!=seen)begin
                pending<=1;capturing<=0;calibrated<=0;status<=1;state<=IDLE;
            end else begin
                if(user && pending)begin
                    pending<=0;capturing<=1;
                    for(j=0;j<6;j=j+1)begin lows[j]<=255;highs[j]<=0;end
                end
                if(user && capturing)begin
                    capturing<=0;
                    if(!complete)begin status<=6;state<=IDLE;end
                    else begin
                        status<=2;state<=SETUP;line_no<=0;any_contrast<=0;have_anchor<=0;
                    end
                end
                case(state)
                    SETUP:begin
                        if(({1'b0,highs[line_no]}-{1'b0,lows[line_no]})<24)advance_line();
                        else begin
                            any_contrast<=1;cut<=({1'b0,highs[line_no]}+{1'b0,lows[line_no]})>>1;
                            clear_index<=0;state<=CLEAR;address<={line_no,7'b0};
                            pos<=0;lane<=0;in_tick<=0;have_center<=0;run_width<=0;eligible<=0;
                        end
                    end
                    CLEAR:begin
                        if(clear_index==31)state<=FETCH;else clear_index<=clear_index+1'b1;
                    end
                    FETCH:state<=WAIT_READ;
                    WAIT_READ:state<=PIXEL;
                    PIXEL:begin
                        if(word[31-lane*8-:8]<cut)begin
                            if(!in_tick)begin start<=pos;run_width<=1;in_tick<=1;end
                            else if(run_width<512)run_width<=run_width+1'b1;
                        end else if(in_tick)begin
                            in_tick<=0;
                            if(start!=0)begin
                                if(run_width>8)have_center<=0;
                                else begin
                                    if(add_gap)eligible<=eligible+1'b1;
                                    have_center<=1;last_center<=center;
                                end
                            end
                        end
                        if(pos==511)begin
                            state<=SCAN;scan_index<=0;window_count<=0;window_weight<=0;
                            best_count<=0;best_weight<=0;
                            delay0<=0;delay1<=0;delay2<=0;delay3<=0;delay4<=0;
                        end else begin
                            pos<=pos+1'b1;lane<=lane+1'b1;
                            if(lane==3)begin address<=address+1'b1;state<=FETCH;end
                        end
                    end
                    SCAN:begin
                        window_count<=count_next;window_weight<=weight_next;
                        delay4<=delay3;delay3<=delay2;delay2<=delay1;delay1<=delay0;delay0<=incoming;
                        if(scan_index>=2 && count_next>best_count)begin best_count<=count_next;best_weight<=weight_next;end
                        if(scan_index==30)state<=RATIO;else scan_index<=scan_index+1'b1;
                    end
                    RATIO:begin
                        if(best_count>=24 && best_weight>=256 &&
                           ({best_count,2'b0}>=( {2'b0,eligible} + {1'b0,eligible,1'b0})))begin
                            dividend<=best_weight*16'd50+(best_count>>1);denominator<=best_count[7:0];
                            quotient<=0;remainder<=0;step<=0;state<=DIVIDE;
                        end else advance_line();
                    end
                    DIVIDE:begin
                        dividend<={dividend[14:0],1'b0};quotient<=qnext;
                        remainder<=qbit?trial-{2'b0,denominator}:trial;
                        if(step==15)begin
                            if(qnext>=200 && qnext<=1600)begin
                                if(have_anchor && difference<=8)begin
                                    span<=(qnext+anchor+1'b1)>>1;calibrated<=1;status<=3;state<=IDLE;
                                end else begin anchor<=qnext[10:0];have_anchor<=1;advance_line();end
                            end else advance_line();
                        end else step<=step+1'b1;
                    end
                endcase
            end
        end
    end
endmodule
