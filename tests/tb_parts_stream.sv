`timescale 1ns/1ps
module tb_parts_stream;
reg clk=0;always #5 clk=~clk;
reg rst=0,v=0,u=0,l=0;reg[95:0]rgb=0;reg[18:0]cfg={3'd6,8'd80,8'd130};
wire[95:0]od;wire ov,ou,ol;wire ir;
edge_control_stream #(.IMG_WIDTH(1280),.IMG_HEIGHT(720),.OSD_ENABLE(0),.DENOISE_ENABLE(1),.NMS_ENABLE(1),.QUALITY_ENABLE(1),.QUALITY_HOPS(4),.TEMPORAL_ENABLE(1),.COLOR_COMPARE_ENABLE(1),.INSPECTION_ENABLE(1),.AUTO_DIMENSION(1),.USABILITY_ENABLE(1),.INSPECTION_V4(1),.VISION_ENABLE(1),.INSPECTION_V5(1),.COMPACT_FONT(1)) dut(
 .clk(clk),.rst_n(rst),.requested_config(cfg),.I_fifo_event_counts(32'd0),.I_switch(4'd0),.I_measure_key_n(1'b1),
 .I_data(rgb),.I_valid(v),.I_user(u),.I_last(l),.O_data(od),.O_valid(ov),.O_user(ou),.O_last(ol),.I_ready(ir),.O_ready(1'b0));
reg[3:0]ui=0;
reg[95:0]gold[0:30];reg[30:0]ev=0,eu=0,el=0,checkq=0;
integer n=0,fr,x,y,k,i,verified=0;reg[95:0]din,expected;
function[23:0]pixel(input integer f,xx,yy);
 reg hit;begin
 hit=(f==1 || f==2)?(xx>=320&&xx<640&&yy>=224&&yy<416):
     (f==3)?(xx>=640&&xx<960&&yy>=224&&yy<416):0;
 if(f>=6)begin hit=(xx>=400&&xx<800&&yy>=240&&yy<304)||(xx>=560&&xx<640&&yy>=304&&yy<480);pixel=hit?24'h141414:24'hc8c8c8;end
 else pixel=hit?24'hc8c8c8:24'h3c3c3c;
 end endfunction
function[23:0]goldpixel(input integer f,xx,yy);
 reg change;begin
 change=(f==2)?(xx>=320&&xx<640):(f==4)?(xx>=320&&xx<960):(f==5)?(xx>=640&&xx<960):0;
 change=change&&yy>=224&&yy<416;
 goldpixel=change && xx%8>=1 && xx%8<=3 && yy%8>=1 && yy%8<=3?24'hff3000:pixel(f,xx,yy);
 end endfunction
task beat(input vv,uu,ll,input[95:0]data,ex,input compare);
 begin @(negedge clk);v=vv;u=uu;l=ll;rgb=data;@(posedge clk);#1;
 for(i=30;i>0;i=i-1)gold[i]=gold[i-1];gold[0]=ex;
 ev={ev[29:0],vv};eu={eu[29:0],uu};el={el[29:0],ll};checkq={checkq[29:0],compare};
 if(ov!==ev[30] || ou!==eu[30] || ol!==el[30] || ir!==1)$fatal(1,"stream timing cycle%d",n);
 if(ov&&checkq[30])begin
  if(od!==gold[30])$fatal(1,"stream fr%d x%d y%d got%h expected%h",fr,x,y,od,gold[30]);verified=verified+1;
 end
 n=n+1;end
endtask
initial begin
 force dut.ui_switches=ui;force dut.ui_span_x=11'd500;force dut.ui_span_y=11'd500;force dut.ui_calibrated=1;force dut.ui_cal_status=3;
 repeat(8)@(negedge clk);rst=1;
 for(fr=0;fr<8;fr=fr+1)begin
  cfg={fr<6?3'd6:3'd0,8'd80,8'd130};ui=fr<6?0:2;
  beat(0,1,0,0,0,0);repeat(40)beat(0,0,0,0,0,0);
  for(y=0;y<720;y=y+1)begin
   for(x=0;x<1280;x=x+4)begin
    for(k=0;k<4;k=k+1)begin din[95-k*24-:24]=pixel(fr,x+k,y);expected[95-k*24-:24]=goldpixel(fr,x+k,y);end
    beat(1,0,x==1276,din,expected,fr<6);
   end
   beat(0,0,0,0,0,0);
   if(fr==7&&y==32)begin
    if(!dut.g_color_compare.u_compare.parts || !dut.g_color_compare.u_compare.formatted)$fatal(1,"T profile not integrated");
    if(dut.g_color_compare.u_compare.digits[0]!==20'h00800 || dut.g_color_compare.u_compare.digits[1]!==20'h00480 ||
       dut.g_color_compare.u_compare.digits[2]!==20'h00160 || dut.g_color_compare.u_compare.digits[3]!==20'h00128 ||
       dut.g_color_compare.u_compare.digits[4]!==20'h00320 || dut.g_color_compare.u_compare.digits[5]!==20'h00320 ||
       dut.g_color_compare.u_compare.digits[6]!==20'h00352)$fatal(1,"T scale/field wiring");
   end
  end
 end
 repeat(40)beat(0,0,0,0,0,0);
 $display("PASS 8 full720p actual31-cycle streams, %d motion beats exact; T profile/calibration/7 fields integrated",verified);$finish;
end
endmodule
