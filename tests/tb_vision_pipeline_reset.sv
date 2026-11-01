`timescale 1ns/1ps
module tb_vision_pipeline_reset;
reg clk=0;always #5 clk=~clk;
reg rn=0,v=0,u=0,l=0;reg[95:0]rgb=0;
wire[95:0]out;wire ov,ou,ol;
edge_control_stream #(.IMG_WIDTH(64),.IMG_HEIGHT(16),.OSD_ENABLE(0),.DENOISE_ENABLE(1),.NMS_ENABLE(1),
 .QUALITY_ENABLE(1),.TEMPORAL_ENABLE(1),.VISION_ENABLE(1)) dut(
 .clk(clk),.rst_n(rn),.requested_config(19'h05082),.I_fifo_event_counts(32'd0),.I_switch(4'd0),
 .I_measure_key_n(1'b1),.I_data(rgb),.I_valid(v),.I_user(u),.I_last(l),.O_data(out),.O_valid(ov),.O_user(ou),.O_last(ol),.O_ready(1'b1));
localparam DEPTH=29; // 27 algorithm + 2 disabled status stages; compare layer off.
reg[95:0]gold[0:DEPTH-1];reg[DEPTH-1:0]gv=0,gu=0,gl=0;
integer i,n,cycles=0,checked=0;reg[31:0]seed=32'hab123456;
task step;input reset_n,tv,tu,tl;begin
 @(negedge clk);rn=reset_n;v=tv;u=tu;l=tl;
 seed={seed[30:0],seed[31]^seed[21]^seed[1]^seed[0]};rgb={seed,seed^32'habcdef12,seed+32'd9876};
 @(posedge clk);#1;
 if(!rn)begin gv=0;gu=0;gl=0;end
 else begin
  for(i=DEPTH-1;i>0;i=i-1)gold[i]=gold[i-1];gold[0]=rgb;
  gv={gv[DEPTH-2:0],tv};gu={gu[DEPTH-2:0],tu};gl={gl[DEPTH-2:0],tl};
 end
 if({ov,ou,ol}!=={gv[DEPTH-1],gu[DEPTH-1],gl[DEPTH-1]})$fatal(1,"FAIL reset metadata cycle%0d",cycles);
 if(ov)begin if(out!==gold[DEPTH-1])$fatal(1,"FAIL reset pixel cycle%0d",cycles);checked=checked+1;end
 cycles=cycles+1;
end endtask
initial begin
 repeat(4)step(0,0,0,0);
 // First valid immediately after reset, then mid-row reset with pipeline full.
 for(n=0;n<91;n=n+1)step(1,1,n==0,n%16==15);
 step(0,0,0,0);step(1,1,1,0);
 for(n=1;n<256;n=n+1)step(1,1,0,n%16==15);
 repeat(35)step(1,0,0,0);
 step(0,0,0,0);step(0,0,0,0);step(1,0,1,0);
 for(n=0;n<256;n=n+1)begin step(1,1,0,n%16==15);if(n%13==7)step(1,0,0,0);end
 repeat(35)step(1,0,0,0);
 $display("PASS reset/first-valid/inline-early SOF/valid gaps pixel and control: %0d cycles %0d beats",cycles,checked);$finish;
end
endmodule
