// Read a horizontal METRIC 1-mm ruler, black ticks on a light matte surface.
// Three 512-pixel scan lines, adaptive threshold, uniform-spacing validation.
// Two independent lines must agree. No OCR, no perspective correction.
// span is pixels per 100 mm; shared X/Y requires perpendicular square-pixel view.
module ruler_auto_calibration #(
    parameter WIDTH=1280,HEIGHT=720,X0=384,Y0=304,LINE_STEP=2
)(input clk,rst_n,input [31:0] gray,input valid,user,last,
  input enable,input request_toggle,
  output reg [10:0] span,output reg calibrated,output reg [2:0] status);
    // 0 required, 1 awaiting full frame, 2 reading, 3 OK, 4 no ticks,
    // 5 irregular/ambiguous ticks, 6 invalid stream, 7 cancelled.
    reg [31:0] memory[0:383];
    reg [10:0] x,y;wire [10:0] px=user?0:x,py=user?0:y;
    reg pending,capturing,seen,armed,bad,finished;
    reg [17:0] beats;
    wire complete=armed && finished && !bad && beats==(WIDTH/4)*HEIGHT;
    wire geometry=last!=(px==WIDTH-4);
    reg [7:0] low,high;reg [7:0] beat_low,beat_high;
    integer k;
    always @*begin
        beat_low=255;beat_high=0;
        for(k=0;k<4;k=k+1)begin
            if(gray[31-k*8-:8]<beat_low)beat_low=gray[31-k*8-:8];
            if(gray[31-k*8-:8]>beat_high)beat_high=gray[31-k*8-:8];
        end
    end
    wire sample_line=py==Y0 || py==Y0+LINE_STEP || py==Y0+2*LINE_STEP;
    wire [1:0] capture_line=py==Y0?0:py==Y0+LINE_STEP?1:2;
    wire [8:0] write_address={capture_line,7'b0}+((px-X0)>>2);
    always @(posedge clk)begin
        if(capturing && enable && valid && !user && sample_line && px>=X0 && px<X0+512)
            memory[write_address]<=gray;
    end
    localparam IDLE=0,FETCH=1,WAIT_READ=2,PIXEL=3,LINE_END=4,DIVIDE=5,DECIDE=6;
    reg [2:0] state;
    reg [8:0] address;reg [31:0] word;
    // Synchronous read, no reset of memory array; never read before full capture.
    always @(posedge clk)word<=memory[address];
    reg [7:0] cut;reg [1:0] line_no,lane;reg [8:0] pos,start;
    reg in_tick,line_bad;reg [9:0] run_width;
    reg [7:0] ticks;reg [9:0] first_center,last_center,min_gap,max_gap;
    wire [9:0] center={1'b0,start}+{1'b0,pos}-1'b1; // doubled center coordinate
    wire [9:0] gap=center-last_center;
    reg [10:0] spans[0:2];reg [2:0] good;
    reg [15:0] dividend,quotient;reg [8:0] remainder;
    reg [7:0] denominator;reg [4:0] step;
    wire [9:0] trial={remainder,dividend[15]};
    wire qbit=trial>={2'b0,denominator};
    wire [15:0] qnext={quotient[14:0],qbit};
    wire pair01=good[0] && good[1] &&
        ((spans[0]>=spans[1]?spans[0]-spans[1]:spans[1]-spans[0])<=8);
    wire pair02=good[0] && good[2] &&
        ((spans[0]>=spans[2]?spans[0]-spans[2]:spans[2]-spans[0])<=8);
    wire pair12=good[1] && good[2] &&
        ((spans[1]>=spans[2]?spans[1]-spans[2]:spans[2]-spans[1])<=8);
    wire [11:0] sum_pair=pair01?{1'b0,spans[0]}+{1'b0,spans[1]}:
        pair02?{1'b0,spans[0]}+{1'b0,spans[2]}:{1'b0,spans[1]}+{1'b0,spans[2]};
    always @(posedge clk or negedge rst_n)begin
        if(!rst_n)begin
            x<=0;y<=0;pending<=0;capturing<=0;seen<=0;armed<=0;bad<=0;finished<=0;beats<=0;
            span<=0;calibrated<=0;status<=0;low<=255;high<=0;state<=IDLE;
            address<=0;cut<=0;line_no<=0;lane<=0;pos<=0;start<=0;in_tick<=0;
            line_bad<=0;run_width<=0;ticks<=0;first_center<=0;last_center<=0;
            min_gap<=1023;max_gap<=0;good<=0;spans[0]<=0;spans[1]<=0;spans[2]<=0;
            dividend<=0;quotient<=0;remainder<=0;denominator<=1;step<=0;
        end else begin
            seen<=request_toggle;
            // Full source-frame validator, including early and inline SOF.
            if(user)begin
                x<=valid?4:0;y<=0;armed<=1;bad<=valid && geometry;
                beats<=valid?1:0;finished<=0;
            end else if(valid)begin
                if(!armed || finished || geometry)bad<=1;
                if(beats<(WIDTH/4)*HEIGHT+1)beats<=beats+1'b1;
                x<=px==WIDTH-4?0:px+4;
                if(px==WIDTH-4)begin y<=py+1'b1;if(py==HEIGHT-1)finished<=1;end
            end else if(last)bad<=1;
            if(capturing && valid && sample_line && px>=X0 && px<X0+512)begin
                if(beat_low<low)low<=beat_low;if(beat_high>high)high<=beat_high;
            end
            if(!enable)begin
                if(pending || capturing || state!=IDLE)status<=7;
                pending<=0;capturing<=0;state<=IDLE;
            end else if(request_toggle!=seen)begin
                // A new request invalidates the old scale; no automatic success on switch exit.
                pending<=1;capturing<=0;calibrated<=0;status<=1;state<=IDLE;
            end else begin
                if(user && pending)begin pending<=0;capturing<=1;low<=255;high<=0;end
                if(user && capturing)begin
                    capturing<=0;
                    if(!complete)begin status<=6;state<=IDLE;end
                    else if(({1'b0,high}-{1'b0,low})<48)begin status<=4;state<=IDLE;end
                    else begin
                        cut<=({1'b0,high}+{1'b0,low})>>1;status<=2;
                        state<=FETCH;address<=0;line_no<=0;pos<=0;lane<=0;
                        in_tick<=0;line_bad<=0;ticks<=0;run_width<=0;
                        first_center<=0;last_center<=0;min_gap<=1023;max_gap<=0;good<=0;
                    end
                end
                case(state)
                    FETCH:state<=WAIT_READ;
                    WAIT_READ:state<=PIXEL;
                    PIXEL:begin
                        if(word[31-lane*8-:8]<cut)begin
                            if(!in_tick)begin start<=pos;run_width<=1;in_tick<=1;end
                            else if(run_width<512)run_width<=run_width+1'b1;
                        end else if(in_tick)begin
                            in_tick<=0;
                            // Ignore a clipped run at the left edge, never invent a center.
                            if(start!=0)begin
                                if(run_width>6 || ticks==255)line_bad<=1;
                                else begin
                                    if(ticks==0)first_center<=center;
                                    else begin
                                        if(gap<min_gap)min_gap<=gap;
                                        if(gap>max_gap)max_gap<=gap;
                                    end
                                    last_center<=center;ticks<=ticks+1'b1;
                                end
                            end
                        end
                        if(pos==511)begin state<=LINE_END;end
                        else begin
                            pos<=pos+1'b1;lane<=lane+1'b1;
                            if(lane==3)begin address<=address+1'b1;state<=FETCH;end
                        end
                    end
                    LINE_END:begin
                        // At least 15 one-mm intervals; pitch 2..16 pixels.
                        // All intervals must agree to <=1 pixel. Missing ticks fail.
                        if(!line_bad && ticks>=16 && min_gap>=4 && max_gap<=32 && max_gap<=min_gap+2)begin
                            dividend<=(last_center-first_center)*16'd50+((ticks-1)>>1);
                            denominator<=ticks-1;quotient<=0;remainder<=0;step<=0;state<=DIVIDE;
                        end else begin
                            good[line_no]<=0;
                            if(line_no==2)state<=DECIDE;
                            else begin
                                line_no<=line_no+1'b1;address<={line_no+2'd1,7'b0};state<=FETCH;
                                pos<=0;lane<=0;in_tick<=0;line_bad<=0;ticks<=0;run_width<=0;
                                first_center<=0;last_center<=0;min_gap<=1023;max_gap<=0;
                            end
                        end
                    end
                    DIVIDE:begin
                        dividend<={dividend[14:0],1'b0};quotient<=qnext;
                        remainder<=qbit?trial-{2'b0,denominator}:trial;
                        if(step==15)begin
                            spans[line_no]<=qnext[10:0];good[line_no]<=qnext>=200 && qnext<=1600;
                            if(line_no==2)state<=DECIDE;
                            else begin
                                line_no<=line_no+1'b1;address<={line_no+2'd1,7'b0};state<=FETCH;
                                pos<=0;lane<=0;in_tick<=0;line_bad<=0;ticks<=0;run_width<=0;
                                first_center<=0;last_center<=0;min_gap<=1023;max_gap<=0;
                            end
                        end else step<=step+1'b1;
                    end
                    DECIDE:begin
                        state<=IDLE;
                        if(pair01 || pair02 || pair12)begin span<=(sum_pair+1'b1)>>1;calibrated<=1;status<=3;end
                        else begin calibrated<=0;status<=5;end
                    end
                endcase
            end
        end
    end
endmodule
