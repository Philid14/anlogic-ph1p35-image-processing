// Empty-plane grayscale reference at16x16 cells. All pixels contribute to
// training; inference compares EVERY pixel with its saved cell mean. Both
// darker and brighter differences are foreground. Not recovery of clipping.
// Two output cycles, statistics branch only. No image/video backpressure.
module measure_background #(
 parameter WIDTH=1280,HEIGHT=720,X0=256,X1=1024,Y0=160,Y1=544,DELTA=12
)(input clk,rst_n,input[31:0]gray,input[3:0]fallback_pixels,
 input valid,user,last,bright,input learn_enable,clear,request_toggle,
 output reg[3:0]pixels,output reg out_valid,out_user,out_last,
 output reg applied,output reg ready,output reg[2:0]status);
 localparam COLS=(X1-X0)/16,CELLS=COLS*((Y1-Y0)/16);
 reg[10:0]x,y;wire[10:0]px=user?0:x,py=user?0:y;
 wire in_area=px>=X0 && px<X1 && py>=Y0 && py<Y1;
 wire geometry=last!=(px==WIDTH-4);
 reg armed,bad,finished,pending,capturing,seen,frame_use;
 reg[11:0]cells_written;
 // x/y advance only on valid. Finished+geometry+no-extra-beat already proves
 // exact raster size; a second full-frame beat counter is redundant.
 wire complete=armed && finished && !bad && cells_written==CELLS;
 reg[15:0]row_sum[0:COLS-1];reg[11:0]horizontal;
 wire[10:0]col=(px-X0)>>4;
 wire[10:0]address=((py-Y0)>>4)*COLS+col;
 wire[9:0]beat_sum={2'b0,gray[31:24]}+{2'b0,gray[23:16]}+{2'b0,gray[15:8]}+{2'b0,gray[7:0]};
 wire[11:0]hsum=(px[3:0]==0?12'd0:horizontal)+beat_sum;
 wire[15:0]vsum=(py[3:0]==0?16'd0:row_sum[col])+hsum;
 wire[16:0]rounded={1'b0,vsum}+17'd128;
 wire block_end=capturing && valid && in_area && px[3:0]==12;
 wire cell_end=block_end && py[3:0]==15;
 wire[7:0]background;
 PH1P_LOGIC_ERAM #(.DATA_WIDTH_A(8),.DATA_WIDTH_B(8),.ADDR_WIDTH_A(11),.ADDR_WIDTH_B(11),
 .DATA_DEPTH_A(2048),.DATA_DEPTH_B(2048),.MODE("DP"),.CLKMODE("SYNC"),.REGMODE_A("NOREG"),.REGMODE_B("NOREG"),
 .INIT_FILE("NONE"),.FILL_ALL("NONE"),.FORCE_KEEP("ON")) u_reference(
 .clka(clk),.cea(cell_end),.ocea(1'b1),.addra(address),.dia(rounded[15:8]),.wea(1'b1),.rsta(1'b0),.bea(1'b1),.doa(),
 .clkb(clk),.ceb(valid && in_area && frame_use && !capturing),.oceb(1'b1),.addrb(address),.dib(8'd0),.web(1'b0),.rstb(1'b0),.beb(1'b1),.dob(background),
 .ecc_sbiterrinj(1'b0),.ecc_dbiterrinj(1'b0),.ecc_sbiterr(),.ecc_dbiterr());
 always @(posedge clk)if(block_end)row_sum[col]<=vsum;
 reg[31:0]gray_d;reg[3:0]fallback_d;reg v_d,u_d,l_d,bright_d,use_d,in_area_d;
 reg[7:0]sample,difference;integer k;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin
   x<=0;y<=0;armed<=0;bad<=0;finished<=0;pending<=0;capturing<=0;seen<=0;frame_use<=0;
   cells_written<=0;horizontal<=0;ready<=0;status<=0;
   gray_d<=0;fallback_d<=0;v_d<=0;u_d<=0;l_d<=0;bright_d<=0;use_d<=0;in_area_d<=0;
   pixels<=0;out_valid<=0;out_user<=0;out_last<=0;applied<=0;
  end else begin
   seen<=request_toggle;
   gray_d<=gray;fallback_d<=fallback_pixels;v_d<=valid;u_d<=user;l_d<=last;bright_d<=bright;
   use_d<=user?(ready && !capturing && !clear):frame_use;in_area_d<=in_area;
   out_valid<=v_d;out_user<=u_d;out_last<=l_d;applied<=use_d;
   for(k=0;k<4;k=k+1)begin
    sample=gray_d[31-k*8-:8];difference=sample>=background?sample-background:background-sample;
    pixels[3-k]<=use_d && in_area_d ? ((difference>=DELTA)^!bright_d):fallback_d[3-k];
   end
   if(user)begin
    x<=valid?4:0;y<=0;armed<=1;bad<=valid && geometry;finished<=0;
    frame_use<=ready && !capturing && !clear;
   end else if(valid)begin
    if(!armed || finished || geometry)bad<=1;
    x<=px==WIDTH-4?0:px+4;
    if(px==WIDTH-4)begin y<=py+1'b1;if(py==HEIGHT-1)finished<=1;end
   end else if(last)bad<=1;
   if(valid && in_area && capturing)horizontal<=hsum;
   if(cell_end)cells_written<=cells_written+1'b1;
   if(clear)begin ready<=0;pending<=0;capturing<=0;frame_use<=0;status<=0;end
   else if(request_toggle!=seen && learn_enable)begin
    ready<=0;pending<=1;capturing<=0;frame_use<=0;status<=1;
   end else if(!learn_enable && (pending || capturing))begin pending<=0;capturing<=0;status<=4;end
   else begin
    if(user && pending)begin pending<=0;capturing<=1;cells_written<=0;horizontal<=0;status<=2;end
    if(user && capturing)begin capturing<=0;ready<=complete;status<=complete?3:4;end
   end
  end
 end
endmodule

