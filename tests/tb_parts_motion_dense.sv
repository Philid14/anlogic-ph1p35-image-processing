`timescale 1ns/1ps
module tb_parts_motion_dense;
reg clk=0;always #5 clk=~clk;
reg rst_n=0;reg[31:0]gray=0;reg valid=0,sof=0,eof=0,abort=0,good=0;
reg[10:0]x=0;reg[9:0]y=0;reg[31:0]fid=0;
wire[3:0]mark;wire ready,rv;wire[31:0]rf;wire[11:0]count;wire[2:0]state;
vision_motion_grid #(.WIDTH(96),.HEIGHT(32),.DENSE_MARK(1)) dut(
 .clk(clk),.rst_n(rst_n),.gray(gray),.valid(valid),.sof(sof),.eof(eof),.abort(abort),.frame_good(good),.x(x),.y(y),.frame_id(fid),
 .mark(mark),.result_ready(ready),.result_valid(rv),.result_frame(rf),.changed_cells(count),.result_state(state));
integer f,r,i=0,vv,ss,ee,aa,gg,xx,yy,ff,er,ec,es;reg[3:0]em;reg[31:0]g;string file;
initial begin
 if(!$value$plusargs("VECTORS=%s",file))$fatal(1,"vectors");f=$fopen(file,"r");
 repeat(8)@(negedge clk);rst_n=1;
 while(!$feof(f))begin
  r=$fscanf(f,"%h %d %d %d %d %d %d %d %d %h %d %d %d\n",g,vv,ss,ee,aa,gg,xx,yy,ff,em,er,ec,es);
  if(r!=13)$fatal(1,"read %d",r);
  @(negedge clk);gray=g;valid=vv;sof=ss;eof=ee;abort=aa;good=gg;x=xx;y=yy;fid=ff;
  @(posedge clk);#1;
  if(mark!==em || ready!==er[0])$fatal(1,"cycle%d mark%h expected%h ready%d/%d x%d y%d",i,mark,em,ready,er,x,y);
  if(ready && (count!==ec[11:0] || state!==es[2:0]))$fatal(1,"result count%d/%d state%d/%d",count,ec,state,es);
  i=i+1;
 end
 $display("PASS dense LAST map %d cycles; no history after abort",i);$finish;
end
endmodule
