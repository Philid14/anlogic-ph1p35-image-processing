`timescale 1ns/1ps
module tb_vision_observer;
reg clk=0;always #5 clk=~clk;
reg rst_n=0,v=0,u=0,l=0;reg[95:0]rgb=0;reg[31:0]gray=0;
wire[3:0]tm,mm;wire[1:0]ts;wire tv,mr,mv;wire[10:0]tx;wire[9:0]ty;
wire[19:0]tn;wire[31:0]tf,mf;wire[11:0]mn;wire[2:0]ms;wire toggle,error;
vision_source_observer #(.WIDTH(128),.HEIGHT(64),.MAX_AGE_CYCLES(8000)) dut(
 .clk(clk),.rst_n(rst_n),.rgb(rgb),.gray(gray),.valid(v),.user(u),.last(l),
 .target_mark(tm),.motion_mark(mm),.track_state(ts),.target_valid(tv),.target_x(tx),.target_y(ty),
 .target_count(tn),.target_frame(tf),.motion_ready(mr),.motion_valid(mv),.motion_count(mn),
 .motion_state(ms),.motion_frame(mf),.complete_toggle(toggle),.protocol_error(error));
integer fd,rc,rr,vv,uu,ll,et,em,check,estate,ecx,ecy,ecount,eframe,en,ems,ev,expected_toggle,checks=0,cycles=0;
reg[95:0]d;reg[31:0]g;reg[3:0]previous_mm=0;reg[2047:0]path;
initial begin
if(!$value$plusargs("STIM=%s",path))$fatal(1,"STIM");fd=$fopen(path,"r");
while(!$feof(fd))begin
 rc=$fscanf(fd,"%d %d %d %d %h %h %d %d %d %d %d %d %d %d %d %d %d %d\n",
 rr,vv,uu,ll,d,g,et,em,check,estate,ecx,ecy,ecount,eframe,en,ems,ev,expected_toggle);
 if(rc==18)begin
  @(negedge clk);rst_n=rr;v=vv;u=uu;l=ll;rgb=d;gray=g;
  @(posedge clk);#1;cycles=cycles+1;
  if(rr && (tm!==et[3:0] || mm!==previous_mm))$fatal(1,"mask cycle%0d got%h/%h expected%h/%h state%0d",cycles,tm,mm,et[3:0],previous_mm,ts);
  previous_mm=em[3:0];
  if(check)begin
   if(ts!==estate[1:0] || tx!==ecx || ty!==ecy || tn!==ecount || tf!==eframe || mn!==en || ms!==ems || mv!==ev[0] || toggle!==expected_toggle[0])
    $fatal(1,"summary%0d state%0d xy%0d/%0d count%0d frame%0d motion%0d/%0d/%0d toggle%0d",checks,ts,tx,ty,tn,tf,mn,ms,mv,toggle);
   checks=checks+1;
  end
 end else if(!$feof(fd))$fatal(1,"parse");
end
$display("PASS vision observer %0d frame checks / %0d cycles: red motion/absence/cancel/geometry/timeout",checks,cycles);$finish;
end
endmodule
