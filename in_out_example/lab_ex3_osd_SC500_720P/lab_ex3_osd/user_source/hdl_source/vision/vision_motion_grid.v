// MAIN: 32x16 full-pixel block means, two history banks, no frame RGB store.
// Input is the normalized 4PPC observer stream. Mask marks the last beat of
// each changed block in compatibility mode. Dense mode renders an 8px-pitch
// dot lattice from the LAST complete motion map, not from a partial current map.
module vision_motion_grid #(
    parameter WIDTH=1280,HEIGHT=720,THRESHOLD=12,MIN_CELLS=3,DENSE_MARK=0
)(input clk,rst_n,input [31:0] gray,input valid,sof,eof,abort,frame_good,
  input [10:0] x,input [9:0] y,input [31:0] frame_id,
  output reg [3:0] mark,output reg result_ready,result_valid,
  output reg [31:0] result_frame,output reg [11:0] changed_cells,
  output reg [2:0] result_state);
    localparam COLS=WIDTH/32,ROWS=HEIGHT/16,CELLS=COLS*ROWS;
    reg [16:0] row_sums[0:COLS-1];
    reg bank,history_valid,pair_valid;
    reg [31:0] previous_frame;
    reg [12:0] horizontal;
    reg [11:0] address;
    wire [8:0] history_data;wire [7:0] old_mean=history_data[7:0];reg [7:0] current_mean;
    reg [10:0] write_address,row_base;
    reg [3:0] dots_d;reg dots_valid;
    wire [10:0] view_address=row_base+(x>>5);
    wire block_start=valid && x[4:0]==0;
    reg [3:0] dots;integer dot_lane;
    always @*begin
        dots=0;
        for(dot_lane=0;dot_lane<4;dot_lane=dot_lane+1)
            dots[3-dot_lane]=(y[2:0]>=1 && y[2:0]<=3) &&
                (((x+dot_lane)&7)>=1 && ((x+dot_lane)&7)<=3);
    end
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
    // 4096x8 true dual-port history: each bank occupies 2048 addresses.
    // Write current bank and synchronously read the other bank at the SAME
    // cell address. No read/write collision; no reset of RAM contents.
    PH1P_LOGIC_ERAM #(.DATA_WIDTH_A(DENSE_MARK?9:8),.DATA_WIDTH_B(DENSE_MARK?9:8),.ADDR_WIDTH_A(12),.ADDR_WIDTH_B(12),
      .DATA_DEPTH_A(4096),.DATA_DEPTH_B(4096),.MODE("DP"),.CLKMODE("SYNC"),
      .REGMODE_A("NOREG"),.REGMODE_B("NOREG"),.INIT_FILE("NONE"),.FILL_ALL("NONE"),.FORCE_KEEP("ON")) u_history(
      .clka(clk),.cea((DENSE_MARK?cell_pending:cell_end) && !abort),.ocea(1'b1),
      .addra({bank,(DENSE_MARK?write_address:address[10:0])}),
      .dia(DENSE_MARK?{changed,current_mean}:{1'b0,rounded[16:9]}),.wea(1'b1),.rsta(1'b0),.bea(1'b1),.doa(),
      .clkb(clk),.ceb((cell_end || (DENSE_MARK && block_start)) && !abort),.oceb(1'b1),
      .addrb({!bank,(cell_end?address[10:0]:view_address)}),
      .dib(9'd0),.web(1'b0),.rstb(1'b0),.beb(1'b1),.dob(history_data),
      .ecc_sbiterrinj(1'b0),.ecc_dbiterrinj(1'b0),.ecc_sbiterr(),.ecc_dbiterr());
    // RAM contents never reset. A bank becomes history only after full valid EOF.
    always @(posedge clk)begin
        if(block_end && !abort)row_sums[x>>5]<=vsum;
    end
    always @(posedge clk or negedge rst_n)begin
        if(!rst_n)begin
            bank<=0;history_valid<=0;pair_valid<=0;previous_frame<=0;horizontal<=0;address<=0;
            current_mean<=0;cell_pending<=0;cell_eligible<=0;eof_pending<=0;good_pending<=0;
            frame_pending<=0;count<=0;mark<=0;result_ready<=0;result_valid<=0;
            result_frame<=0;changed_cells<=0;result_state<=0;
            write_address<=0;row_base<=0;dots_d<=0;dots_valid<=0;
        end else begin
            mark<=DENSE_MARK?(dots_valid && !abort && history_data[8]?dots_d:4'd0):(changed?4'b1111:4'b0000);
            dots_d<=dots;dots_valid<=valid && pair_valid && !abort;
            if(cell_end)write_address<=address[10:0];
            if(valid && x==WIDTH-4 && y[3:0]==15)row_base<=row_base+COLS;
            result_ready<=0;
            cell_pending<=cell_end && !abort;
            cell_eligible<=pair_valid && !abort;
            eof_pending<=eof;good_pending<=frame_good && !abort;
            if(eof)frame_pending<=frame_id;
            if(valid)horizontal<=hsum;
            if(cell_end && !abort)begin current_mean<=rounded[16:9];address<=address+1'b1;end
            if(changed)count<=count+1'b1;
            if(sof)begin
                row_base<=0;
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
