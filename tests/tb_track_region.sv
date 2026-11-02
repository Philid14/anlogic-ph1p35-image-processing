`timescale 1ns/1ps
module tb_track_region;
 parameter WIDTH=160,HEIGHT=120;
 reg clk=0;always #5 clk=~clk;
 reg rst=0,v=0,u=0,l=0;reg[95:0]rgb=0;
 wire[43:0]box;wire tv,err;wire[1:0]state;wire[10:0]tx;wire[9:0]ty;
 wire[19:0]count;wire[31:0]fid;
 vision_source_observer #(.WIDTH(WIDTH),.HEIGHT(HEIGHT),.MAX_AGE_CYCLES(6000000)) dut(
 .clk(clk),.rst_n(rst),.rgb(rgb),.gray(32'd0),.valid(v),.user(u),.last(l),
 .target_box(box),.target_valid(tv),.track_state(state),.target_x(tx),.target_y(ty),
 .target_count(count),.target_frame(fid),.target_mark(),.motion_mark(),
 .motion_ready(),.motion_valid(),.motion_count(),.motion_state(),.motion_frame(),
 .complete_toggle(),.protocol_error(err));
 integer fd,rc,n,f,x,y,a,b,c,d,area,inline_sof,frames=0,pxchecks=0;
 reg[2047:0]path;reg[95:0]data;
 task step;input vv,uu,ll;input[95:0]dd;
 begin @(negedge clk);v=vv;u=uu;l=ll;rgb=dd;@(posedge clk);#1;end endtask
 initial begin
  if(!$value$plusargs("STIM=%s",path))$fatal(1,"STIM");fd=$fopen(path,"r");
  repeat(8)@(negedge clk);rst=1;
  while(!$feof(fd))begin
   rc=$fscanf(fd,"%d %d %d %d %d %d\n",a,b,c,d,area,inline_sof);
   if(rc==6)begin
    if(!inline_sof)step(0,1,0,0);
    for(y=0;y<HEIGHT;y=y+1)begin
     for(x=0;x<WIDTH;x=x+4)begin
      rc=$fscanf(fd,"%h\n",data);if(rc!=1)$fatal(1,"data parse");
      // Realistic valid gaps and both SOF forms; last row has no spare beat.
      if(((x+y)%37)==3)step(0,0,0,0);
      step(1,inline_sof&&x==0&&y==0,x==WIDTH-4,data);pxchecks=pxchecks+1;
     end
    end
    repeat(12)step(0,0,0,0);
    if(err)$fatal(1,"unexpected protocol error");
    if(count!==area || tx!==(area?(a+b)/2:0) || ty!==(area?(c+d)/2:0) ||
       box!==(area?{11'(a),11'(b),11'(c),11'(d)}:44'd0))
      $fatal(1,"f%0d bbox=%h xy=%0d/%0d area=%0d expected%0d/%0d/%0d/%0d area%0d",frames,box,tx,ty,count,a,b,c,d,area);
    if(!area&&tv)$fatal(1,"empty frame retained box");
    frames=frames+1;
   end else if(!$feof(fd))$fatal(1,"header parse");
  end
  // Malformed source clears an acquired target; no coordinate carryover.
  step(0,1,0,0);step(1,0,1,{4{24'he02020}});repeat(12)step(0,0,0,0);
  if(!err||tv||box!=0)$fatal(1,"malformed source did not invalidate");
  $display("PASS region model %0d frames %0d beats; sparse red/warm neutral/moving circle/multiple regions/borders/early-inline SOF/gaps/abort",frames,pxchecks);$finish;
 end
endmodule
