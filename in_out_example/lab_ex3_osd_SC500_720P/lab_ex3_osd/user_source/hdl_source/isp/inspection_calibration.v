// Manual two-axis ruler calibration. Known interval is explicitly 100.0 mm.
// SW1 enable, SW3 CAL, SW2 selects X(0)/Y(1) in CAL. K2 short -4px;
// hold +4px/repeat. Leaving CAL with both axes visited confirms the spans.
// No automatic ruler recognition, persistence, perspective or height model.
module inspection_calibration(
    input clk,rst_n,input[3:0] switches,input short_toggle,up_toggle,
    output reg[10:0] span_x,span_y,output reg calibrated,
    output reg[1:0] visited
);
    reg previous_cal,seen_short,seen_up;
    wire cal_mode=switches[1] && switches[3];
    wire inc=up_toggle!=seen_up,dec=short_toggle!=seen_short;
    always @(posedge clk or negedge rst_n)begin
        if(!rst_n)begin
            span_x<=256;span_y<=256;calibrated<=0;visited<=0;
            previous_cal<=0;seen_short<=0;seen_up<=0;
        end else begin
            previous_cal<=cal_mode;seen_short<=short_toggle;seen_up<=up_toggle;
            if(cal_mode)begin
                calibrated<=0;
                if(!previous_cal)visited<=switches[2]?2'b10:2'b01;
                else visited<=visited | (switches[2]?2'b10:2'b01);
                if(inc || dec)begin
                    if(switches[2])begin
                        if(inc && span_y<352)span_y<=span_y+4;
                        else if(dec && !inc && span_y>16)span_y<=span_y-4;
                    end else begin
                        if(inc && span_x<736)span_x<=span_x+4;
                        else if(dec && !inc && span_x>16)span_x<=span_x-4;
                    end
                end
            end else if(previous_cal)calibrated<=switches[1] && visited==2'b11;
        end
    end
endmodule
