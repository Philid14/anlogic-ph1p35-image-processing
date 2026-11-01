// MAIN: 32x16 full-pixel block means, two history banks, no frame RGB store.
// Input is the normalized 4PPC observer stream. Mask marks the last beat of
// each changed block; complete statistics publish after EOF, never mid-frame.
module vision_motion_grid #(
    parameter WIDTH=1280,HEIGHT=720,THRESHOLD=12,MIN_CELLS=3
)(input clk,rst_n,input [31:0] gray,input valid,sof,eof,abort,frame_good,
  input [10:0] x,input [9:0] y,input [31:0] frame_id,
  output reg [3:0] mark,output reg result_ready,result_valid,
  output reg [31:0] result_frame,output reg [11:0] changed_cells,
  output reg [2:0] result_state);
    localparam COLS=WIDTH/32,ROWS=HEIGHT/16,CELLS=COLS*ROWS;
    reg [16:0] row_sums[0:COLS-1];
    reg [7:0] bank0[0:CELLS-1],bank1[0:CELLS-1];
    reg bank,history_valid,pair_valid;
    reg [31:0] previous_frame;
    reg [12:0] horizontal;
    reg [11:0] address;
    reg [7:0] old_mean,current_mean;
    reg cell_pending,cell_eligible,eof_pending,good_pending;
    reg [31:0] frame_pending;
    reg [11:0] count;
    wire [9:0] beat_sum={2'b0,gray[31:24]}+{2'b0,gray[23:16]}+
                          {2'b0,gray[15:8]}+{2'b0,gray[7:0]};
    wire [12:0] hsum=(x[4:0]==0?13'd0:horizontal)+beat_sum;
    wire [16:0] vsum=(y[3:0]==0?17'd0:row_sums[x>>5])+hsum;
    wire [17:0] rounded={1'b0,vsum}+18'd256;
    wire block_end=valid && x[4:0]==28;
    wire cell_end=block_end && y[3:0]==15;
    wire [7:0] difference=current_mean>=old_mean?current_mean-old_mean:old_mean-current_mean;
    wire changed=cell_pending && cell_eligible && difference>=THRESHOLD;
    wire [12:0] final_count={1'b0,count}+changed;
    // RAM contents never reset. A bank becomes history only after full valid EOF.
    always @(posedge clk)begin
        if(block_end && !abort)row_sums[x>>5]<=vsum;
        if(cell_end && !abort)begin
            if(bank)begin bank1[address]<=rounded[16:9];old_mean<=bank0[address];end
            else begin bank0[address]<=rounded[16:9];old_mean<=bank1[address];end
        end
    end
    always @(posedge clk or negedge rst_n)begin
        if(!rst_n)begin
            bank<=0;history_valid<=0;pair_valid<=0;previous_frame<=0;horizontal<=0;address<=0;
            current_mean<=0;cell_pending<=0;cell_eligible<=0;eof_pending<=0;good_pending<=0;
            frame_pending<=0;count<=0;mark<=0;result_ready<=0;result_valid<=0;
            result_frame<=0;changed_cells<=0;result_state<=0;
        end else begin
            mark<=changed?4'b1111:4'b0000;
            result_ready<=0;
            cell_pending<=cell_end && !abort;
            cell_eligible<=pair_valid && !abort;
            eof_pending<=eof;good_pending<=frame_good && !abort;
            if(eof)frame_pending<=frame_id;
            if(valid)horizontal<=hsum;
            if(cell_end && !abort)begin current_mean<=rounded[16:9];address<=address+1'b1;end
            if(changed)count<=count+1'b1;
            if(sof)begin
                count<=0;horizontal<=beat_sum;address<=0;
                pair_valid<=history_valid && frame_id==previous_frame+1'b1;
            end
            if(abort)begin history_valid<=0;pair_valid<=0;count<=0;mark<=0;cell_pending<=0;end
            if(eof_pending)begin
                result_ready<=1;result_valid<=good_pending;result_frame<=frame_pending;
                if(good_pending)begin
                    bank<=!bank;history_valid<=1;previous_frame<=frame_pending;
                    changed_cells<=pair_valid?final_count[11:0]:12'd0;
                    result_state<=!pair_valid?1:final_count*4>CELLS*3?4:final_count>=MIN_CELLS?3:2;
                end else begin history_valid<=0;changed_cells<=0;result_state<=0;end
            end
        end
    end
endmodule
