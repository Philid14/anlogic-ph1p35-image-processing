`timescale 1ns/1ps
module tb_parts_views;
reg enabled;reg[15:0]fid;reg[33:0]coords;wire[43:0]sizes,box,gaps;wire[1:0]gv;wire[2:0]kind;
parts_measure_view dut(.enabled(enabled),.sample_id(fid),.sizes({11'd400,11'd240,22'h12345}),
 .box_coords({11'd400,11'd799,11'd240,11'd479}),.gap_coords(44'h12345678abc),.gap_valid(2'b11),.part_coords(coords),
 .view_sizes(sizes),.view_box(box),.view_gap_coords(gaps),.view_gap(gv),.kind(kind));
integer f,r,en,id,ek,n=0;reg[43:0]eb,es;string file;
initial begin
 if(!$value$plusargs("VECTORS=%s",file))$fatal(1,"vectors");f=$fopen(file,"r");
 while(!$feof(f))begin
  r=$fscanf(f,"%d %d %h %d %h %h\n",en,id,coords,ek,eb,es);if(r!=6)$fatal(1,"read");
  enabled=en;fid=id;#1;
  if(kind!==ek[2:0] || box!==eb || sizes!==es)$fatal(1,"view %d kind%d/%d box%h/%h sizes%h/%h",n,kind,ek,box,eb,sizes,es);
  if(kind!=0 && (gaps!==0 || gv!==0))$fatal(1,"partial gap leakage");
  if(kind==0 && (gaps!==44'h12345678abc || gv!==3))$fatal(1,"bypass changed");
  n=n+1;
 end
 $display("PASS %d view phases, all T/L orientations, 32-source-frame dwell, holes/bypass",n);$finish;
end
endmodule
