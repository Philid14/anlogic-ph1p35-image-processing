`timescale 1ns/1ps
module tb_inspection_track;
 reg clk=0;always #5 clk=~clk;
 reg rst=0,v=0,u=0,l=0;reg[95:0]rgb=0;
 wire[43:0]bbox;wire tv;wire[1:0]state;wire[10:0]tx;wire[9:0]ty;wire[19:0]count;wire[31:0]fid;
 wire[95:0]out_rgb;wire ov,ou,ol,err;
 vision_source_observer #(.WIDTH(128),.HEIGHT(96),.MAX_AGE_CYCLES(10000)) observer(
 .clk(clk),.rst_n(rst),.rgb(rgb),.gray(32'd0),.valid(v),.user(u),.last(l),.target_box(bbox),
 .target_valid(tv),.track_state(state),.target_x(tx),.target_y(ty),.target_count(count),.target_frame(fid),
 .target_mark(),.motion_mark(),.motion_ready(),.motion_valid(),.motion_count(),.motion_state(),.motion_frame(),.complete_toggle(),.protocol_error(err));
 edge_status_osd #(.IMG_WIDTH(128),.IMG_HEIGHT(96),.VISION_ENABLE(1),.COMPACT_FONT(1),.INSPECTION_V5(1)) osd(
 .clk(clk),.rst_n(rst),.I_data(rgb),.I_valid(v),.I_user(u),.I_last(l),.I_config({3'd5,8'd80,8'd130}),
 .I_fifo_event_counts(0),.I_switches(0),.I_ruler_status(0),.I_track_state(state),.I_target_valid(tv),
 .I_target_x(tx),.I_target_y(ty),.I_target_count(count),.I_target_frame(fid),.I_target_box(bbox),
 .I_motion_valid(0),.I_motion_count(0),.I_motion_state(0),.I_motion_frame(0),.I_observer_error(err),
 .O_data(out_rgb),.O_valid(ov),.O_user(ou),.O_last(ol));
 integer f,x,y,k,n=0,oldleft=0,left,borders=0,clears=0;reg lock_valid=0;
 reg[95:0]expect0=0,e;reg v0=0,u0=0,l0=0;
 task step;input vv,uu,ll;input[95:0]d,expected;
 begin
  @(negedge clk);v=vv;u=uu;l=ll;rgb=d;
  @(posedge clk);#1;
  if(ov!==v0||ou!==u0||ol!==l0)$fatal(1,"track metadata %0d",n);
  if(ov&&out_rgb!==expect0)$fatal(1,"track pixel %0d got%h exp%h",n,out_rgb,expect0);
  expect0=expected;v0=vv;u0=uu;l0=ll;n=n+1;
 end endtask
 reg[95:0]data;
 initial begin
  repeat(8)@(negedge clk);rst=1;
  for(f=0;f<9;f=f+1)begin
   left=f<4?20:f==4?40:f==5?60:24;
   lock_valid=tv;
   if(lock_valid)begin
    if(bbox!=={11'(oldleft),11'(oldleft+23),11'd32,11'd55}||tx!=oldleft+11||ty!=43||count!=576)$fatal(1,"bbox result/frame mismatch f%0d %h",f,bbox);
   end
   if(f==7&&tv)$fatal(1,"absent target did not clear");
   step(0,1,0,0,0);repeat(5)step(0,0,0,0,0);
   for(y=0;y<96;y=y+1)begin
    for(x=0;x<128;x=x+4)begin
     data=0;e=0;
     for(k=0;k<4;k=k+1)begin
      data[95-k*24-:24]=(f!=6&&x+k>=left&&x+k<left+24&&y>=32&&y<56)?24'he02020:24'h607090;
      e[95-k*24-:24]=data[95-k*24-:24];
      if(lock_valid&&x+k>=oldleft&&x+k<=oldleft+23&&y>=32&&y<=55&&
         (x+k<=oldleft+1||x+k>=oldleft+22||y<=33||y>=54))begin e[95-k*24-:24]=24'h00ff80;borders=borders+1;end
     end
     step(1,0,x==124,data,e);
    end
    step(0,0,0,0,0);
   end
   repeat(10)step(0,0,0,0,0);oldleft=left;
  end
  if(borders==0)$fatal(1,"no visible outline");
  repeat(11000)step(0,0,0,0,0);
  if(tv)$fatal(1,"stale source not expired");
  $display("PASS red moving LAST bbox, exact pixels/metadata, disappearance, stale guard, preserved red interior %0d borders",borders);$finish;
 end
endmodule
