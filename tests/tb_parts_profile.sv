`timescale 1ns/1ps
module tb_parts_profile;
reg clk=0;always #5 clk=~clk;
reg rst_n=0,v=0,u=0,l=0;reg[3:0]pixels=0;wire pv,rv,present;wire[33:0]coords;wire[43:0]box;
planar_measure_stats #(.WIDTH(512),.HEIGHT(256),.X0(40),.X1(460),.Y0(32),.Y1(224),.COMPACT_COUNT(1),.PARTS_ENABLE(1),.MIN_ROW(6)) dut(
 .clk(clk),.rst_n(rst_n),.binary_pixels(pixels),.valid(v),.user(u),.last(l),.bright(1'b1),.threshold(8'd130),
 .result_valid(rv),.present(present),.box_coords(box),.part_valid(pv),.part_coords(coords));
integer f,e,r,fr,x,y,ee,eb,expected;reg[3:0]mask;reg[33:0]ec;reg[43:0]bc;string dir;
task beat(input vv,uu,ll,input[3:0]p);
 begin @(negedge clk);v=vv;u=uu;l=ll;pixels=p;@(posedge clk);#1;end
endtask
initial begin
 if(!$value$plusargs("DIR=%s",dir))$fatal(1,"dir");f=$fopen({dir,"/stim.txt"},"r");e=$fopen({dir,"/expected.txt"},"r");
 repeat(6)@(negedge clk);rst_n=1;beat(0,1,0,0);
 for(fr=0;fr<14;fr=fr+1)begin
  for(y=0;y<256;y=y+1)begin
   for(x=0;x<512;x=x+4)begin
    r=$fscanf(f,"%h %d\n",mask,eb);if(r!=2)$fatal(1,"stim");beat(1,0,eb,mask);
    if((x/4+y)%71==0)beat(0,0,0,0);
   end
   beat(0,0,0,0);
  end
  beat(0,1,0,0);r=$fscanf(e,"%d %h %h\n",expected,ec,bc);
  if(pv!==expected[0] || (pv && (coords!==ec || box!==bc)))$fatal(1,"frame%d parts%d/%d coords%h/%h box%h/%h",fr,pv,expected,coords,ec,box,bc);
 end
 $display("PASS 14 T/L profiles, reflection hole, rectangle/rotation/taper/gap/short/malformed rejection and recovery");$finish;
end
endmodule
